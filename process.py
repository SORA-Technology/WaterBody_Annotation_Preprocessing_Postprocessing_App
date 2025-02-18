# process.py
import os
import json
import rasterio
import numpy as np
import streamlit as st  # IMPORTANT: for manual progress updates
from pyproj import Transformer
from shapely.geometry import box
from PIL import Image, ImageDraw
from typing import Tuple, List
from rasterio.windows import Window
import time
import shutil

from logger import Logger
logger = Logger("TIFF_PROCESSOR")


def load_coordinates(geojson_path: str) -> List[List[float]]:
    """Load the GeoJSON file and extract latitude/longitude data."""
    try:
        logger.info(f"Loading GeoJSON file from {geojson_path}")
        with open(geojson_path, 'r', encoding='utf-8') as file:
            geojson_data = json.load(file)
    except FileNotFoundError:
        logger.error(f"GeoJSON file not found: {geojson_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {geojson_path}. Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading GeoJSON file: {geojson_path}. Error: {e}")
        raise

    coordinates = []
    for feature in geojson_data.get('features', []):
        geometry = feature.get('geometry', {})
        if geometry.get('type') == 'Point':
            coord = geometry.get('coordinates', [])
            if len(coord) == 2 and all(isinstance(x, (int, float)) for x in coord):
                # [lat, lon]
                coordinates.append([coord[1], coord[0]])
    logger.success(f"Loaded {len(coordinates)} coordinates from the GeoJSON file.")
    return coordinates


def latlon_to_rowcol(lat: float, lon: float, transform: rasterio.Affine) -> Tuple[int, int]:
    """Convert latitude/longitude to row/column indices in the TIFF."""
    try:
        col, row = ~transform * (lon, lat)
        return int(row), int(col)
    except Exception as e:
        logger.error(f"Error converting lat/lon ({lat}, {lon}) to row/col. {e}")
        raise


def calculate_window_size(target_file_size: int, bands: int, dtype_bytes: int) -> int:
    """Calculate the window size to achieve the target file size (in bytes)."""
    try:
        logger.info(f"Calculating window size for target file size: {target_file_size} bytes")
        return int((target_file_size / (bands * dtype_bytes)) ** 0.5)
    except ZeroDivisionError:
        logger.error("Division by zero while calculating window size.")
        raise
    except Exception as e:
        logger.error(f"Error calculating window size. Error: {e}")
        raise


def create_unique_windows(points: List[Tuple[int, int]],
                          window_size: int,
                          tiff_height: int,
                          tiff_width: int
) -> Tuple[List[Window], List[List[Tuple[int, int]]]]:
    """
    Create windows so that each point appears in exactly one window.
    """
    logger.info(f"Creating unique windows with size: {window_size}")
    used_points = set()
    processed_windows = []
    window_points_list = []

    for (row, col) in points:
        if (row, col) in used_points:
            continue

        row_start = max(row - window_size // 2, 0)
        row_end   = min(row + window_size // 2, tiff_height)
        col_start = max(col - window_size // 2, 0)
        col_end   = min(col + window_size // 2, tiff_width)

        if row_end <= row_start or col_end <= col_start:
            logger.error(f"Invalid window for point ({row}, {col}). Skipping.")
            continue

        contained_points = []
        for (r2, c2) in points:
            if (r2, c2) not in used_points:
                if (row_start <= r2 < row_end) and (col_start <= c2 < col_end):
                    contained_points.append((r2, c2))

        if len(contained_points) == 0:
            continue

        for pt in contained_points:
            used_points.add(pt)

        new_window = Window(
            col_off=col_start,
            row_off=row_start,
            width=col_end - col_start,
            height=row_end - row_start
        )

        processed_windows.append(new_window)
        window_points_list.append(contained_points)

    logger.success(f"Created {len(processed_windows)} windows, each with unique points.")
    return processed_windows, window_points_list


def save_tiff_and_png(src: rasterio.io.DatasetReader,
                      window: Window,
                      idx: int,
                      tiff_crs: rasterio.crs.CRS,
                      points: List[Tuple[int,int]],
                      region: str,
                      base_output_folder: str) -> None:
    """Save the divided TIFF and a PNG with red dots for each point."""
    logger.info(f"Saving TIFF/PNG for window index: {idx}")

    tiff_dir = os.path.join(base_output_folder, region, "tiff")
    png_dir  = os.path.join(base_output_folder, region, "png")
    ann_dir  = os.path.join(base_output_folder, region, "for_annotation")

    for d in [tiff_dir, png_dir, ann_dir]:
        os.makedirs(d, exist_ok=True)

    tiff_out_path = os.path.join(tiff_dir, f"{region}_divided_image_{idx}.tif")
    png_out_path  = os.path.join(png_dir,  f"{region}_divided_image_{idx}.png")
    ann_out_path  = os.path.join(ann_dir,  f"{region}_divided_image_{idx}.png")
    red_color = (255, 0, 0)

    try:
        data = src.read(window=window)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": window.height,
            "width": window.width,
            "transform": src.window_transform(window),
            "crs": tiff_crs
        })

        # Save the new TIFF
        with rasterio.open(tiff_out_path, "w", **out_meta) as dest:
            dest.write(data)
        logger.success(f"Saved TIFF file: {tiff_out_path}")

        # Create PNG from the raster
        if data.shape[0] >= 3:
            # multi-band
            img = Image.fromarray(data.transpose(1, 2, 0))
        else:
            # single-band
            img = Image.fromarray(data[0])

        # Resize to match window dimensions (optional)
        img = img.resize((window.width, window.height), Image.LANCZOS)
        img.save(png_out_path)
        logger.success(f"Saved PNG file: {png_out_path}")

        # Annotate with points
        draw = ImageDraw.Draw(img)
        count = 0
        for row, col in points:
            if 0 <= row < window.height and 0 <= col < window.width:
                draw.ellipse((col - 20, row - 20, col + 20, row + 20), fill=red_color)
                count += 1
        img.save(ann_out_path)
        logger.success(f"Saved annotated PNG with {count} points: {ann_out_path}")

    except Exception as e:
        logger.error(f"Failed to save TIFF and PNG for window {idx}. Error: {e}")


def resize_images(input_folder, output_folder, size=(1024, 1024)):
    """
    Manually track progress in Streamlit (removing tqdm).
    """
    logger.info(f"Resizing images in {input_folder} -> {output_folder}")
    os.makedirs(output_folder, exist_ok=True)

    # Get the list of files we want to resize
    files_in_folder = [f for f in os.listdir(input_folder)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    total_files = len(files_in_folder)
    if total_files == 0:
        logger.info("No images found for resizing.")
        return

    progress_bar = st.progress(0)  # new progress bar
    status_text = st.empty()

    start_time = time.time()

    count_resized = 0
    for i, filename in enumerate(files_in_folder, start=1):
        img_path = os.path.join(input_folder, filename)
        if os.path.getsize(img_path) < 500 * 1024:
            logger.info(f"Skipping {filename} as it is smaller than 500KB")
        else:
            try:
                img = Image.open(img_path)
                img_resized = img.resize(size, Image.LANCZOS)
                img_resized.save(os.path.join(output_folder, filename))
                count_resized += 1
                logger.success(f"Resized {filename}")
            except Exception as e:
                logger.error(f"Error resizing {filename}: {e}")

        # Update progress for each file
        elapsed = time.time() - start_time
        avg_time_per_file = elapsed / i
        remaining = total_files - i
        eta_seconds = remaining * avg_time_per_file

        progress_percent = int((i / total_files) * 100)
        progress_bar.progress(progress_percent)

        status_text.text(
            f"Resizing images: {i}/{total_files} done. "
            f"Elapsed: {elapsed:.1f}s | ETA: {eta_seconds:.1f}s"
        )

    logger.success(f"Resized {count_resized}/{total_files} images in {input_folder}.")


def process_tiff_and_geojson(geojson_bytes,
                             tiff_bytes,
                             region_name: str,
                             output_folder: str):
    """
    Main function that:
      1. Saves uploaded bytes -> temp files
      2. Loads coordinates from GeoJSON
      3. Opens TIFF, reprojects points
      4. Creates windows & saves sub-TIFF/PNGs (with manual progress)
      5. Resizes images for annotation (with manual progress)
    """
    # 1) Save to temp
    geojson_temp = "temp_uploaded.geojson"
    tiff_temp    = "temp_uploaded.tif"
    with open(geojson_temp, 'wb') as f:
        f.write(geojson_bytes)
    with open(tiff_temp, 'wb') as f:
        f.write(tiff_bytes)

    # 2) Load coords
    coordinates = load_coordinates(geojson_temp)
    if not coordinates:
        raise ValueError("No valid coordinates found in the GeoJSON.")

    latitudes, longitudes = zip(*coordinates)

    # 3) Open TIFF & reproject
    with rasterio.open(tiff_temp) as src:
        tiff_transform = src.transform
        tiff_crs = src.crs
        logger.info(f"TIFF CRS: {tiff_crs}")

        transformer = Transformer.from_crs("EPSG:4326", tiff_crs, always_xy=True)
        tiff_dtype  = src.dtypes[0]
        tiff_bands  = src.count
        tiff_height = src.height
        tiff_width  = src.width
        dtype_bytes = np.dtype(tiff_dtype).itemsize

        # Convert lat/lon -> row/col
        points = []
        for lat, lon in zip(latitudes, longitudes):
            try:
                lon_reproj, lat_reproj = transformer.transform(lon, lat)
                row, col = latlon_to_rowcol(lat_reproj, lon_reproj, tiff_transform)
                if 0 <= row < tiff_height and 0 <= col < tiff_width:
                    points.append((row, col))
                else:
                    logger.warning(
                        f"Point {lat},{lon} => out-of-bounds (row={row}, col={col}). Skipped."
                    )
            except Exception as e:
                logger.error(f"Error reprojecting point ({lat},{lon}): {e}")

        logger.info(f"Total valid points after conversion: {len(points)}")
        if not points:
            raise ValueError("No in-bounds points found for the TIFF.")

        # 4) Create windows & manually track progress
        target_file_size = 100 * 1024 * 1024
        window_size = calculate_window_size(target_file_size, tiff_bands, dtype_bytes)
        processed_windows, window_points_list = create_unique_windows(points,
                                                                      window_size,
                                                                      tiff_height,
                                                                      tiff_width)

        total_windows = len(processed_windows)
        if total_windows == 0:
            logger.warning("No windows created - no further processing.")
            return

        # Streamlit progress for slicing
        slicing_progress_bar = st.progress(0)
        slicing_status_text = st.empty()
        slicing_start = time.time()

        for idx, (window, abs_points) in enumerate(
            zip(processed_windows, window_points_list), start=1
        ):
            # Convert absolute -> window-relative
            window_points = [(r - window.row_off, c - window.col_off) for (r, c) in abs_points]

            # Save subwindow
            save_tiff_and_png(src, window, idx, tiff_crs, window_points, region_name, output_folder)

            # Update slicing progress
            elapsed = time.time() - slicing_start
            avg_time_per_win = elapsed / idx
            remaining = total_windows - idx
            eta_seconds = remaining * avg_time_per_win
            eta_min = int(eta_seconds // 60)
            eta_sec = int(eta_seconds % 60)
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)


            progress_percent = int((idx / total_windows) * 100)
            slicing_progress_bar.progress(progress_percent)

            slicing_status_text.text(
                f"Slicing TIFF: {idx}/{total_windows} windows processed. "
                f"Elapsed: {elapsed_min}m: {elapsed_sec:.1f}s | ETA: {eta_min}m {eta_sec}s"
            )

    # 5) Resize annotation images with manual progress
    ann_folder   = os.path.join(output_folder, region_name, "for_annotation")
    resized_dest = os.path.join(output_folder, region_name, "resized_png")
    resize_images(ann_folder, resized_dest)

    # 6) **Delete the `for_annotation` folder** after successful processing
    if os.path.exists(ann_folder):
        try:
            shutil.rmtree(ann_folder)  
            logger.success(f"Deleted temporary folder: {ann_folder}")
        except Exception as e:
            logger.error(f"Error deleting folder {ann_folder}: {e}")
