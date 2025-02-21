# visualize_coco.py (for example)

import os
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from PIL import Image
import streamlit as st

# Example color map
label_colors = {
    "Drainage ditches": (255, 0, 0),   # Red
    "Dry rice field": (0, 128, 0),     # Green
    "Wet rice field": (0, 0, 255),     # Blue
    "Other agricultural field": (255, 255, 0),  # Yellow
    "Swampy area": (128, 0, 128),      # Purple
    "Reservoir": (165, 42, 42),        # Brown
    "Puddle made by rain": (255, 165, 0),  # Orange
    "River (with stream)": (0, 255, 255),  # Cyan
    "River (stagnant)": (128, 128, 128)    # Gray
}

@st.cache_data
def load_coco_annotations(coco_dict, image_dir):
    """
    Converts a loaded COCO JSON dict into a list of image entries 
    we can iterate through for visualization.

    Returns:
      images_list: list of dictionaries, each with:
        {
          'image_path': str,
          'bboxes': list of [x, y, width, height],
          'labels': list of str (category names),
          'attributes': list of dict (the 'attribute' field in your COCO),
          'filename': str
        }
    """

    categories = {cat['id']: cat['name'] for cat in coco_dict['categories']}
    images_list = []

    # Loop over images
    for img_info in coco_dict['images']:
        image_id = img_info['id']
        filename = img_info['file_name']
        image_path = os.path.join(image_dir, filename)

        # Find all annotations for this image
        anns = [ann for ann in coco_dict['annotations'] if ann['image_id'] == image_id]
        
        bboxes = [ann['bbox'] for ann in anns]
        labels = [categories[ann['category_id']] for ann in anns]
        # 'attribute' is custom in your data
        attributes = [ann['attribute'] for ann in anns]

        images_list.append({
            'image_path': image_path,
            'filename': filename,
            'bboxes': bboxes,
            'labels': labels,
            'attributes': attributes
        })

    return images_list


def draw_coco_bboxes(image_path, bboxes, labels, attributes, label_lookup=None):
    """
    Uses OpenCV+Matplotlib to draw bounding boxes on a single image.
    Returns a Matplotlib figure that you can display in Streamlit.
    """

    image = cv2.imread(image_path)
    if image is None:
        # Return None so we can handle in the calling code
        return None

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    overlay = image.copy()

    # 1) Fill overlay rectangles
    for bbox, label in zip(bboxes, labels):
        x, y, w, h = bbox  # these are presumably absolute pixel coords
        color = label_colors.get(label, (0, 255, 0))
        cv2.rectangle(overlay, (int(x), int(y)), (int(x + w), int(y + h)), color, -1)

    alpha = 0.4  # transparency factor
    image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)

    # 2) Draw outlines + text
    for bbox, label, attr in zip(bboxes, labels, attributes):
        x, y, w, h = bbox
        color = label_colors.get(label, (0, 255, 0))
        cv2.rectangle(image, (int(x), int(y)), (int(x + w), int(y + h)), color, 3)
        # Optionally put text / attributes
        # cv2.putText(
        #     image,
        #     label,
        #     (int(x), int(y) - 10),
        #     cv2.FONT_HERSHEY_SIMPLEX,
        #     0.8,
        #     color,
        #     2
        # )
        # ...
        # You can also display the attributes if you want:
        # e.g., for a custom overlay, interpret keys from `attr`.

    # 3) Create a Matplotlib figure to display
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(image)
    ax.axis('off')
    
    # legend
    legend_elements = [plt.Line2D([0], [0], color=np.array(color)/255, lw=4, label=label) 
                       for label, color in label_colors.items()]
    legend = ax.legend(handles=legend_elements, loc='upper right', frameon=True, fontsize=5)
    legend.get_frame().set_alpha(0.4)
    plt.show()

    return fig

# def create_plotly_figure_coco(image_path, bboxes, labels, attributes):
#     """
#     Creates a Plotly figure with:
#       - A background image
#       - Semi-transparent rectangle shapes for each bounding box
#       - Invisible scatter points for hover text
#     """
#     try:
#         img_pil = Image.open(image_path)
#     except:
#         return None

#     width, height = img_pil.size
#     fig = go.Figure()

#     # Add the background image
#     fig.add_layout_image(
#         dict(
#             source=img_pil,
#             xref="x",
#             yref="y",
#             x=0,
#             y=0,
#             sizex=width,
#             sizey=height,
#             sizing="stretch",
#             layer="below"
#         )
#     )

#     # Hide axes if desired
#     fig.update_xaxes(range=[0, width], visible=False)
#     fig.update_yaxes(range=[height, 0], scaleanchor="x", visible=False)

#     shapes = []
#     scatter_x = []
#     scatter_y = []
#     hover_texts = []

#     for bbox, label, attr_dict in zip(bboxes, labels, attributes):
#         x, y, w, h = bbox

#         # Lookup color from label_colors; default to red if missing
#         rgb = label_colors.get(label, (255, 0, 0))
#         # Format as "rgba(r,g,b,alpha)"
#         border_color_str = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},1.0)"  # fully opaque border
#         fill_color_str = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.3)"   # partially transparent fill

#         # Build a rectangle shape
#         shape = {
#             "type": "rect",
#             "x0": x,
#             "y0": y,
#             "x1": x + w,
#             "y1": y + h,
#             "line": {"color": border_color_str, "width": 1},
#             "fillcolor": fill_color_str,
#         }
#         shapes.append(shape)

#         # Place a scatter point in the center for hover text
#         cx = x + w/2
#         cy = y + h/2

#         # If you want to show attributes, build a string
#         attr_str = "<br>".join([f"{k}: {v}" for k, v in attr_dict.items()])

#         text_html = f"<b>{label}</b><br>{attr_str}"
#         scatter_x.append(cx)
#         scatter_y.append(cy)
#         hover_texts.append(text_html)

#     fig.update_layout(shapes=shapes)

#     # Add scatter points for hover
#     fig.add_trace(go.Scatter(
#         x=scatter_x,
#         y=scatter_y,
#         mode="markers",
#         marker=dict(size=10, color="rgba(0,0,0,0)"),  # invisible
#         text=hover_texts,
#         hovertemplate="%{text}<extra></extra>"
#     ))

#     fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
#     return fig