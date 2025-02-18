# post_process.py

import os
import json
from datetime import datetime
import numpy as np
from PIL import Image
import streamlit as st
import time  
from tqdm import tqdm

from logger import Logger
logger = Logger("POST_PROCESSOR")


def create_dir(path: str) -> None:
    """Safely create a directory if it doesn't exist."""
    try:
        os.makedirs(path, exist_ok=True)
        logger.success(f"Directory created or verified: {path}")
    except Exception as e:
        logger.error(f"Failed to create directory: {path} - {e}")


def load_data(input_path: str):
    """Load JSON data from a file."""
    try:
        with open(input_path, 'r') as file:
            data = json.load(file)
        logger.success("Data loaded successfully.")
        return data
    except Exception as e:
        logger.error(f"Failed to load data from {input_path}: {e}")
        return None


def lookup_value(value, lookup_dict, idx):
    """
    If 'value' is a list, fetch the item at 'idx'. 
    If out of range or missing, fallback to the first element or return 'Unknown'.
    """
    if isinstance(value, list):
        if idx < len(value):
            return lookup_dict.get(value[idx], f"Unknown ({value[idx]})")
        else:
            return lookup_dict.get(value[0], f"Unknown ({value[0]})")
    else:
        return lookup_dict.get(value, f"Unknown ({value})")


def getdataFromImage(file_name, image_folder_path, cropped_folder_path, threshold=0) -> tuple:
    """
    Loads an image, crops out thresholded areas (black borders),
    saves the cropped image to another folder,
    returns (height, width, offset_y, offset_x).
    """
    try:
        image_path = os.path.join(image_folder_path, file_name)
        img = Image.open(image_path)
        arr = np.array(img)

        # Identify black areas below threshold
        mask = np.all(arr <= threshold, axis=-1)  # All channels <= threshold
        required = np.logical_not(mask)

        rows = np.any(required, axis=1)
        cols = np.any(required, axis=0)

        if not np.any(rows) or not np.any(cols):
            # No cropping needed; just save original
            cropped_img_path = os.path.join(cropped_folder_path, file_name)
            img.save(cropped_img_path)
            return img.size[1], img.size[0], 0, 0

        min_row, max_row = np.where(rows)[0][[0, -1]]
        min_col, max_col = np.where(cols)[0][[0, -1]]

        cropped_img = img.crop((min_col, min_row, max_col + 1, max_row + 1))
        cropped_img_path = os.path.join(cropped_folder_path, file_name)
        cropped_img.save(cropped_img_path, "PNG")

        return cropped_img.size[1], cropped_img.size[0], min_row, min_col

    except Exception as e:
        logger.error(f"Failed to load/process image: {file_name}. Error: {e}")
        raise e


def convert_to_coco(input_path, output_path, image_folder_path, cropped_folder_path):
    """
    Converts labeled JSON data to COCO format, writes the result to `output_path`,
    and handles image cropping in `cropped_folder_path`, with a progress bar.
    """
    # Example categories
    predefined_categories = {
        'Drainage ditches': 0,
        'Dry rice field': 1,
        'Wet rice field': 2,
        'Other agricultural field': 3,
        'Swampy area': 4,
        'Reservoir': 5,
        'Puddle made by rain': 6,
        'River (with stream)': 7,
        'River (stagnant)': 8
    }

    # Initialize COCO structure
    coco_format = {
        "info": {
            "description": "Converted Dataset",
            "version": "1.0",
            "year": datetime.now().year,
            "contributor": "User",
            "date_created": datetime.now().isoformat()
        },
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [
            {"id": cid, "name": cname, "supercategory": "waterbody"}
            for cname, cid in predefined_categories.items()
        ],
        "attributes": [],
        "lookup": {
            "type": {
                0: "Artificial water body",
                1: "Natural water body"
            },
            "size": {
                0: "Very small water body (< 0.5 m x 0.5 m)",
                1: "Small water body (0.5 m x 0.5 m < 1 m x 1 m)",
                2: "Medium water body (1 m x 1 m < 10 m x 10 m)",
                3: "Large water body (> 10 m x 10 m)"
            },
            "vegetation_inside": {
                0: "None",
                1: "Exist"
            },
            "vegetation_around": {
                0: "None",
                1: "Exist"
            },
            "turbidity": {
                0: "Clean water",
                1: "Turbid water",
                2: "Very turbid water"
            }
        }
    }

    # Lookup dicts
    type_lookup = {
        "Artificial water body": 0,
        "Natural water body": 1
    }
    size_lookup = {
        "Very small water body (< 0.5 m x 0.5 m)": 0,
        "Small water body (0.5 m x 0.5 m < 1 m x 1 m)": 1,
        "Medium water body (1 m x 1 m < 10 m x 10 m)": 2,
        "Large water body (10 m x 10 m < ...)": 3
    }
    vegetation_lookup = {
        "None": 0,
        "Exist": 1
    }
    turbidity_lookup = {
        "Clean water": 0,
        "Turbid water": 1,
        "Very turbid water": 2
    }

    annotation_id = 0
    data = load_data(input_path)
    if data is None:
        logger.error("Failed to load JSON data.")
        return  

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    total_items = len(data)
    if total_items == 0:
        logger.warning("No items found in the JSON data.")
        return

    # Process each item
    for i, item in enumerate(tqdm(data, total=len(data), desc="Converting data to COCO format:"), start=1):
        if "bbox" not in item or not item["bbox"]:
            continue

        file_name = item["image"].split("-")[-1]
        original_image_path = os.path.join(image_folder_path, file_name)
        if not os.path.exists(original_image_path):
            logger.error(f"Image file not found: {original_image_path}")
            # Continue to next item
            continue

        original_image = Image.open(original_image_path)
        orig_width, orig_height = original_image.size

        # Crop
        height, width, offset_y, offset_x = getdataFromImage(
            file_name, image_folder_path, cropped_folder_path, threshold=0
        )
        height, width = int(height), int(width)

        # Add image info
        image_info = {
            "id": item["id"],
            "file_name": file_name,
            "width": width,
            "height": height
        }
        coco_format["images"].append(image_info)

        # BBoxes
        for idx, bbox in enumerate(item["bbox"]):
            category_name = bbox["rectanglelabels"][0]
            category_id = predefined_categories.get(category_name, -1)
            if category_id == -1:
                logger.error(f"Invalid category name: {category_name}")
                continue

            # from % to absolute coords
            x_abs = (bbox["x"] / 100.0) * orig_width
            y_abs = (bbox["y"] / 100.0) * orig_height
            w_abs = (bbox["width"] / 100.0) * orig_width
            h_abs = (bbox["height"] / 100.0) * orig_height

            # Adjust for cropping
            x_abs_adj = x_abs - offset_x
            y_abs_adj = y_abs - offset_y

            annotation = {
                "id": annotation_id,
                "image_id": item["id"],
                "category_id": category_id,
                "bbox": [x_abs_adj, y_abs_adj, w_abs, h_abs],
                "area": w_abs * h_abs,
                "iscrowd": 0,
                "rotation": bbox["rotation"],
                "attribute": {
                    "type": lookup_value(item["type"], type_lookup, idx),
                    "size": lookup_value(item["size"], size_lookup, idx),
                    "vegetation_inside": lookup_value(item["vegetation_inside"], vegetation_lookup, idx),
                    "vegetation_around": lookup_value(item["vegetation_around"], vegetation_lookup, idx),
                    "turbidity": lookup_value(item["turbidity"], turbidity_lookup, idx),
                }
            }
            coco_format["annotations"].append(annotation)
            annotation_id += 1

        # --------------- Update Progress/ETA ---------------
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        avg_time_per_item = elapsed / i
        items_left = total_items - i
        eta_seconds = avg_time_per_item * items_left
        eta_min = int(eta_seconds // 60)
        eta_sec = int(eta_seconds % 60)

        pct_complete = int((i / total_items) * 100)
        progress_bar.progress(pct_complete)

        status_text.text(
            f"Processing item {i}/{total_items} "
            f"(Elapsed {elapsed_min}m {elapsed_sec}s | ETA {eta_min}m {eta_sec}s)"
        )

    # Add attribute lookups
    coco_format["attributes"] = [
        {"attribute_name": "type", "lookup": type_lookup},
        {"attribute_name": "size", "lookup": size_lookup},
        {"attribute_name": "vegetation_inside", "lookup": vegetation_lookup},
        {"attribute_name": "vegetation_around", "lookup": vegetation_lookup},
        {"attribute_name": "turbidity", "lookup": turbidity_lookup}
    ]

    # Save final COCO
    with open(output_path, 'w') as file:
        json.dump(coco_format, file, indent=2)

    logger.success(f"Data successfully converted to COCO format: {output_path}")


def run_postprocessing(
    input_json_bytes: bytes,
    region_name: str,
    post_date: str,
    image_folder_path: str
):
    """
    Single input for `image_folder_path`. 
    We automatically create "final_png" as the cropped_folder_path next to it.
    Then we build the final filename => {region_name}_{post_date}.json
    """
    temp_input_json = "temp_post_input.json"
    with open(temp_input_json, 'wb') as f:
        f.write(input_json_bytes)

    # Build final_png path next to your image_folder_path
    cropped_folder_path = os.path.join(os.path.dirname(image_folder_path), "final_png")
    create_dir(cropped_folder_path)

    # Build the final output filename
    output_filename = f"{region_name}_{post_date}.json"
    output_path = os.path.join(os.getcwd(), output_filename)

    # Convert data => COCO (with progress bar)
    convert_to_coco(
        input_path=temp_input_json,
        output_path=output_path,
        image_folder_path=image_folder_path,
        cropped_folder_path=cropped_folder_path,
    )

    logger.success(f"Postprocessing completed. COCO saved at {output_path}")
    st.success(f"Postprocessing completed. COCO saved at {output_path}")
