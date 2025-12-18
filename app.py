import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil

# --- CONFIGURATION ---
# This finds Tesseract automatically on the Cloud (Linux) or Windows
path = shutil.which("tesseract") 
if path:
    pytesseract.pytesseract.tesseract_cmd = path
else:
    # Fallback for local Windows if not found in PATH
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- UI SETUP ---
st.set_page_config(page_title="Attendance Scanner", page_icon="📸")
st.title("📸 Attendance Scanner")
st.write("For Teachers: Snap a photo of the attendance sheet.")

# --- INPUT METHOD ---
input_method = st.radio("Choose Input:", ["Camera 📸", "Upload File 📂"], horizontal=True)

image = None

if input_method == "Camera 📸":
    camera_file = st.camera_input("Take a photo")
    if camera_file:
        image = Image.open(camera_file)
else:
    upload_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    if upload_file:
        image = Image.open(upload_file)

# --- PROCESSING ---
if image is not None:
    st.write("---")
    st.image(image, caption="Selected Image", use_container_width=True)
    
    if st.button("Generate Excel ✅", type="primary"):
        with st.spinner("👀 Reading text..."):
            try:
                # 1. Image Prep
                img_array = np.array(image)
                # Convert to grayscale
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Increase contrast (Thresholding)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 2. Extract Text
                # psm 6 = Assume a single uniform block of text
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(thresh, config=custom_config)

                # 3. Clean Text into List
                lines = text.split('\n')
                clean_data = []
                for line in lines:
                    if len(line.strip()) > 3: # Ignore empty/tiny lines
                        clean_data.append([line.strip()])

                # 4. Show & Download
                if clean_data:
                    st.success("Success! Data extracted.")
                    df = pd.DataFrame(clean_data, columns=["Raw Attendance Data"])
                    
                    # Editable Table
                    edited_df = st.data_editor(df, num_rows="dynamic")
                    
                    # Download Button
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Excel (CSV)",
                        data=csv,
                        file_name='attendance_list.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("⚠️ No text found. Try a clearer photo with better lighting.")
                    
            except Exception as e:
                st.error(f"Error: {e}")