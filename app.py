import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil
import re
import io

# --- CONFIG ---
st.set_page_config(page_title="Pro Attendance", page_icon="📝", layout="wide")

path = shutil.which("tesseract") 
pytesseract.pytesseract.tesseract_cmd = path if path else r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def fuzzy_extract(text):
    lines = text.split('\n')
    extracted = []
    
    for line in lines:
        # 1. Remove obvious grid noise like | _ [ ] { }
        clean = re.sub(r'[\|_\[\]\{\}\(\)\-\.]', ' ', line)
        clean = " ".join(clean.split())
        
        # 2. FUZZY SEARCH: Look for a Roll Number (4 digits)
        # Then look for Status (P or A) at the end
        # Capture everything in between as the name
        match = re.search(r'(\d{4})\s+(.*?)\s+([PpAa])(?:\s|$)', clean)
        
        if match:
            roll = match.group(1)
            name_raw = match.group(2).strip()
            status = match.group(3).upper()
            
            # 3. Clean the Name: Remove random OCR artifacts like "ea", "nr", "ee"
            name = re.sub(r'\b(ea|nr|ee|ae|gt|fe|sp)\b', '', name_raw, flags=re.I).strip()
            # Remove any non-alphabetic chars from name
            name = re.sub(r'[^a-zA-Z\s]', '', name).strip()
            
            if len(name) > 2:
                extracted.append({"Roll No": roll, "Name": name, "Status": status})
    
    return extracted

st.title("📝 Pro Attendance Scanner")
st.info("Tip: If it fails, try cropping the photo to just the table rows (ignore the header).")

uploaded_file = st.file_uploader("Upload Attendance Photo", type=["jpg", "jpeg", "png"])
cam_file = st.camera_input("Or Take a Photo")

file = cam_file if cam_file else uploaded_file

if file:
    img = Image.open(file)
    st.image(img, caption="Processing...", use_container_width=True)
    
    if st.button("🚀 Generate Excel", type="primary", use_container_width=True):
        with st.spinner("Extracting data..."):
            # Image Preprocessing
            open_cv_image = np.array(img)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            # Resize for better OCR accuracy
            gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            # Thresholding
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # OCR with PSM 6 (uniform block of text)
            raw_text = pytesseract.image_to_string(thresh, config='--oem 3 --psm 6')
            
            data = fuzzy_extract(raw_text)
            
            if data:
                df = pd.DataFrame(data)
                st.success(f"Found {len(df)} records!")
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                # Excel Download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel", output.getvalue(), "Attendance.xlsx", use_container_width=True)
            else:
                st.error("No valid records found. The image might be too blurry or the grid lines too thick.")
                with st.expander("Debug: Raw OCR Text"):
                    st.text(raw_text)






