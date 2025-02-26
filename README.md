# WaterBody Annotation Preprocessing, Postprocessing & Visualization App
Implementation of integrated waterbody annotation data preparation scripts for preprocessing, postprocessing and visualization.

his application streamlines the workflow for:
1. **Pre-Processing**: Splitting a large GeoTIFF based on points in a GeoJSON.
2. **Post-Processing**: Converting JSON-MIN waterbody annotations into standard COCO format.
3. **Visualization**: Inspecting bounding boxes and attributes on your data (both JSON-MIN and COCO formats).

The app is built with **Streamlit** and includes the following Python modules:
- **rasterio** for reading/writing geospatial raster data  
- **shapely** and **pyproj** for coordinate transformations  
- **OpenCV** and **PIL** for image manipulation  
- **matplotlib**/**plotly** for visualization  
- **tqdm** for progress bars  
- **colorama** for colorized logging  

> **Table of Contents**  
> - [Features](#features)  
> - [Quick Start with Docker](#quick-start-with-docker)  
> - [Alternative: Run Locally without Docker](#alternative-run-locally-without-docker)  
> - [App Structure](#app-structure)


---

## Features

1. **Preprocessing**  
   - Accepts a `.tif` (GeoTIFF) and `.geojson`.  
   - Splits the GeoTIFF around each point in the GeoJSON, and optionally resizes those sub-images.

2. **Postprocessing**  
   - Converts your JSON-MIN annotated data into standard COCO format, while automatically cropping black borders around images.

3. **Visualization**  
   - Visualize bounding boxes in either JSON-MIN or COCO format in an interactive, step-by-step manner.

---

### Important: Clone This Repository
Before building the Docker image, clone or download this repo to have all source files locally:
```bash
git clone https://github.com/YourOrgName/waterbodyapp.git
cd waterbodyapp 
```

## Quick Start with Docker

You can run everything inside a Docker container to avoid installing Python dependencies on your local machine.

### 1) Build the Docker image
From your project’s root folder (where the Dockerfile is located):
```bash
docker build -t waterbodyapp .
```

### 2) Run the container
Once the image is built, start the container and map Streamlit’s default port 8501:
```bash 
docker run -p 8501:8501 --name waterbodyapp -v "C:\:/host" --privileged waterbodyapp
```

That’s it! You can now access the app in your browser at:

```
http://localhost:8501
```

### Repository Structure

```
.
├── app.py                # Main Streamlit app
├── process.py            # Preprocessing logic
├── post_process.py       # Postprocessing logic
├── visualize_coco.py     # Visualize COCO annotations
├── visualize_jsonmin.py  # Visualize JSON-MIN annotations
├── logger.py             # Custom color logger
├── Dockerfile            # Docker setup
├── README.md             
```

