
import rasterio.vrt
import rasterio.sample


import streamlit as st
from process import process_tiff_and_geojson as  run_preprocessing
from post_process import run_postprocessing
from logger import Logger

logger = Logger("APP_LOGGER")



def main():

    st.title("***Sora-Tech:*** WaterBody Annotation Preprocessing & Postprocessing App")
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

    mode = st.sidebar.radio("***Select Mode:***", ["Pre-Processing", "Post-Processing"])

    # ---------------------
    # 1) PREPROCESSING MODE
    # ---------------------
    if mode == "Pre-Processing":
        st.subheader("Preprocessing: Split Image Around Points from GeoJSON")
        
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
    else:
        st.subheader("Postprocessing: Convert JSON-MIN labeled data to COCO Format")

        post_json_file = st.file_uploader("***Upload JSON-MIN File***", type=["json"])
        
        region_name   = st.text_input("***Enter Region Name***")
        post_date     = st.text_input("***Enter Date (e.g. 20240728)***")

        # Only ONE folder input for the PNG images
        image_folder_path = st.text_input("***Folder Path to original PNG Images***")

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
            if not image_folder_path.strip():
                st.error("Please specify the path to your PNG images folder.")
                return

            with st.spinner("Postprocessing..."):
                try:
                    run_postprocessing(
                        input_json_bytes=post_json_file.getvalue(),
                        region_name=region_name.strip(),
                        post_date=post_date.strip(),
                        image_folder_path=image_folder_path.strip()
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Error in postprocessing: {e}")
                    logger.error(f"Postprocessing error: {e}")

if __name__ == "__main__":
    main()
