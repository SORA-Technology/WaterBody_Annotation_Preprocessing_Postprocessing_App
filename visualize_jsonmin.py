# visualize_jsonmin.py

import os
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt

label_colors = {
    "Drainage ditches": (255, 0, 0),  
    "Dry rice field": (0, 128, 0),
    "Wet rice field": (0, 0, 255),
    "Other agricultural field": (255, 255, 0),
    "Swampy area": (128, 0, 128),
    "Reservoir": (165, 42, 42),
    "Puddle made by rain": (255, 165, 0),
    "River (with stream)": (0, 255, 255),
    "River (stagnant)": (128, 128, 128)
}

def load_jsonmin_annotations(jsonmin_data, image_dir):
    """
    Returns a list of dict:
      {
        'image_path': str,
        'filename': str,
        'bboxes': list of [x_pixel, y_pixel, w_pixel, h_pixel],
        'labels': list of str,
        'attributes': list of str
      }
    """
    images_list = []
    for annotation in jsonmin_data:
        # The file name logic might differ. Adjust as needed
        # e.g. "regions/1_Takyiman/final_png/my_image.png"
        # or "project-1_image-12345.png"
        # In your snippet, you did something like annotation['image'][9:]
        # so we'll replicate that logic carefully
        full_filename = annotation['image'].split('/')[-1][9:]
        image_path = os.path.join(image_dir, full_filename)

        bboxes = []
        labels = []
        attributes = []

        if os.path.exists(image_path):
            for i, bbox in enumerate(annotation['bbox']):
                label = bbox['rectanglelabels'][0]
                labels.append(label)

                # Convert percentages to pixel values
                x_pct, y_pct = bbox['x'], bbox['y']
                w_pct, h_pct = bbox['width'], bbox['height']
                original_w, original_h = bbox['original_width'], bbox['original_height']
                x_pixel = int(x_pct / 100 * original_w)
                y_pixel = int(y_pct / 100 * original_h)
                w_pixel = int(w_pct / 100 * original_w)
                h_pixel = int(h_pct / 100 * original_h)
                bboxes.append([x_pixel, y_pixel, w_pixel, h_pixel])

                # Build attributes string
                # e.g. "Type: XXX, Size: YYY, Vegetation Inside: ZZZ, ..."
                # from your snippet:
                # annotation['type'][i], annotation['size'][i], etc.
                # but remember to check array lengths
                type_val = annotation['type'][i] if i < len(annotation['type']) else 'N/A'
                size_val = annotation['size'][i] if i < len(annotation['size']) else 'N/A'
                vi_val   = annotation['vegetation_inside'][i] if i < len(annotation['vegetation_inside']) else 'N/A'
                va_val   = annotation['vegetation_around'][i] if i < len(annotation['vegetation_around']) else 'N/A'
                turb_val = annotation['turbidity'][i] if i < len(annotation['turbidity']) else 'N/A'

                attr_str = (f"Type: {type_val}, Size: {size_val}, "
                            f"Vegetation Inside: {vi_val}, Vegetation Around: {va_val}, "
                            f"Turbidity: {turb_val}")
                attributes.append(attr_str)

        images_list.append({
            'image_path': image_path,
            'filename': full_filename,
            'bboxes': bboxes,
            'labels': labels,
            'attributes': attributes
        })

    return images_list

def draw_jsonmin_bboxes(image_path, bboxes, labels, attributes):
    """
    Return a Matplotlib figure with bounding boxes drawn, 
    using your alpha overlay approach.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    overlay = image.copy()

    # 1) Fill rectangles
    for (bbox, label) in zip(bboxes, labels):
        x, y, w, h = bbox
        color = label_colors.get(label, (0, 255, 0))
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)

    alpha = 0.4
    image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)

    # 2) Outline + label
    for (bbox, label, attr_str) in zip(bboxes, labels, attributes):
        x, y, w, h = bbox
        color = label_colors.get(label, (0, 255, 0))
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
        # Draw label
        # cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        # # You could also parse & display attr_str if desired

    # 3) Convert to figure
    fig, ax = plt.subplots(figsize=(8,8))
    ax.imshow(image)
    ax.axis('off')

    # Legend
    legend_elements = [plt.Line2D([0], [0], color=np.array(color)/255, lw=4, label=label) 
                       for label, color in label_colors.items()]
    legend = ax.legend(handles=legend_elements, loc='upper right', frameon=True, fontsize=5)
    legend.get_frame().set_alpha(0.4)
    plt.show()
    
    return fig
