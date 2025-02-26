import rasterio.vrt
import rasterio.sample
import streamlit as st
from process import process_tiff_and_geojson as  run_preprocessing
from post_process import run_postprocessing
from logger import Logger
import json
from visualize_coco import load_coco_annotations, draw_coco_bboxes
from visualize_jsonmin import load_jsonmin_annotations, draw_jsonmin_bboxes

logger = Logger("APP_LOGGER")

@st.cache_data
def parse_coco_json(json_bytes):
    """
    Loads JSON from raw bytes. We'll do this once per unique file.
    """
    return json.loads(json_bytes)


def main():

    st.markdown(
        """
        <style>
        /* Enlarge the radio circle itself */
        div[data-testid="stRadio"] input[type="radio"] {
            transform: scale(1.4) !important;
            margin-right: 6px; /* optional spacing */
        }

        /* Optionally enlarge the label text */
        div[data-testid="stRadio"] label p {
            font-size: 1.8rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    mode = st.sidebar.radio(
        "***Select Mode:***", 
        ["Home", "Pre-Processing", "Post-Processing", "Visualization"]
        )

    if mode == "Home":
        st.title("***Sora-Tech:*** WaterBody Annotation Preprocessing, Postprocessing & Visualization App")
        st.subheader("Welcome to the Sora-Tech WaterBody App!")
        st.write("""
            **Here's how to get started:**

            - **Pre-Processing**: 
              Split a large TIFF image around points from a GeoJSON file. 
              This will produce smaller image patches and annotated PNGs.
            
            - **Post-Processing**: 
              Convert your labeled JSON-MIN data into COCO format. 
              This is helpful if you want standard annotation structures for training or analysis.
            
            - **Visualization**: 
              Visualize your annotations or processed images right in the app.
            
            Use the **sidebar** on the left to pick the mode you want!
        """)


    # ---------------------
    # 1) PREPROCESSING MODE
    # ---------------------
    if mode == "Pre-Processing":
        st.title("***Pre-Processing:*** Split Image Around Points from GeoJSON")
        
        geojson_file = st.file_uploader("***Upload GeoJSON File***", type=["geojson", "json"])
        tiff_file    = st.file_uploader("***Upload TIFF File***", type=["tif", "tiff"])
        
        region_name   = st.text_input("***Enter Region name***")
        output_folder = st.text_input("***Output folder path (This can be changed.)***", value="output")

        if st.button("Run Preprocessing"):
            if not geojson_file:
                st.error("Please upload a GeoJSON file.")
                return
            if not tiff_file:
                st.error("Please upload a TIFF file.")
                return
            if not region_name.strip():
                st.error("Please write the region name before proceeding.")
                return
            if not output_folder.strip():
                st.error("Please provide a valid output folder.")
                return

            with st.spinner("Running Preprocessing..."):
                try:
                    run_preprocessing(
                        geojson_bytes=geojson_file.getvalue(),
                        tiff_bytes=tiff_file.getvalue(),
                        region_name=region_name.strip(),
                        output_folder=output_folder.strip()
                    )
                    st.success("Preprocessing completed successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error in preprocessing: {e}")
                    logger.error(f"Preprocessing error: {e}")

    # ----------------------
    # 2) POSTPROCESSING MODE
    # ----------------------
    elif mode == "Post-Processing":
        st.title("***Post-Processing:*** Convert JSON-MIN labeled data to COCO Format")

        post_json_file = st.file_uploader("***Upload JSON-MIN File***", type=["json"])
        
        region_name   = st.text_input("***Enter Region Name***")
        post_date     = st.text_input("***Enter Date (e.g. 20240728)***")

        # Only ONE folder input for the PNG images
        images_folder_path = st.text_input("***Folder Path to original PNG Images***")

        if st.button("Run Postprocessing"):
            if not post_json_file:
                st.error("Please upload a labeled JSON-MIN file.")
                return
            if not region_name.strip():
                st.error("Region name cannot be empty.")
                return
            if not post_date.strip():
                st.error("Please input the date (e.g. 20240728).")
                return
            if not images_folder_path.strip():
                st.error("Please specify the path to your PNG images folder.")
                return

            with st.spinner("Postprocessing..."):
                try:
                    run_postprocessing(
                        input_json_bytes=post_json_file.getvalue(),
                        region_name=region_name.strip(),
                        post_date=post_date.strip(),
                        images_folder_path=images_folder_path.strip()
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Error in postprocessing: {e}")
                    logger.error(f"Postprocessing error: {e}")
        
    elif mode == "Visualization":
        st.title("Visualization")

        st.write("#### Use the options below to view your annotated images one by one with Next/Previous.")

        viz_mode = st.radio("***Choose Annotation Format:***", ["JSON-MIN", "COCO"], key="viz_mode")
        images_folder_path = st.text_input("***Folder Path to images***")

        if viz_mode == "COCO":
            coco_json = st.file_uploader("Upload COCO JSON", type=["json"])
            if coco_json and images_folder_path.strip():
                # Load the JSON
                coco_data = parse_coco_json(coco_json.read())
                # Convert to list
                images_list = load_coco_annotations(coco_data, images_folder_path)
                if not images_list:
                    st.error("No images found in COCO data.")
                    return

            
                if "coco_idx" not in st.session_state:
                    st.session_state["coco_idx"] = 0
                idx = st.session_state["coco_idx"]
                # Show the current image
                current_item = images_list[idx]
                fig = draw_coco_bboxes(
                    current_item["image_path"],
                    current_item["bboxes"],
                    current_item["labels"],
                    current_item["attributes"]
                )
                if fig is None:
                    st.warning(f"Could not open image: {current_item['image_path']}")
                else:
                    # st.plotly_chart(fig, use_container_width=True)
                    st.pyplot(fig)
                st.write(f"Image {idx+1}/{len(images_list)}: {current_item['filename']}")


                
                col1, col3, col2 = st.columns([1, 3, 1])
                with col1:
                    if st.button("Previous"):
                        st.session_state["coco_idx"] = (idx - 1) % len(images_list)
                        st.rerun()
                with col2:
                    if st.button("Next"):
                        st.session_state["coco_idx"] = (idx + 1) % len(images_list)
                        st.rerun()


        else:
            # JSON-MIN
            jsonmin_file = st.file_uploader("Upload JSON-MIN file", type=["json"])
            if jsonmin_file and images_folder_path.strip():
                jsonmin_data = json.loads(jsonmin_file.read())
                images_list = load_jsonmin_annotations(jsonmin_data, images_folder_path)
                if not images_list:
                    st.error("No images found in JSON-MIN data.")
                    return

                
                if "jsonmin_idx" not in st.session_state:
                    st.session_state["jsonmin_idx"] = 0

                idx = st.session_state["jsonmin_idx"]
                current_item = images_list[idx]
                fig = draw_jsonmin_bboxes(
                    current_item["image_path"],
                    current_item["bboxes"],
                    current_item["labels"],
                    current_item["attributes"]
                )
                if fig is None:
                    st.warning(f"Could not open image: {current_item['image_path']}")
                else:
                    st.pyplot(fig)
                st.write(f"Image {idx+1}/{len(images_list)}: {current_item['filename']}")


                
                col1, col3, col2 = st.columns([1, 3, 1])
                with col1:
                    if st.button("Previous"):
                        st.session_state["jsonmin_idx"] = (idx - 1) % len(images_list)
                        st.rerun()
                with col2:
                    if st.button("Next"):
                        st.session_state["jsonmin_idx"] = (idx + 1) % len(images_list)
                        st.rerun()



if __name__ == "__main__":
    main()
