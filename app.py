import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil
import re
import io

# --- MOBILE & PRO CONFIG ---
st.set_page_config(page_title="Pro Attendance", page_icon="📝", layout="wide")

path = shutil.which("tesseract") 
pytesseract.pytesseract.tesseract_cmd = path if path else r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def remove_grid_lines(image):
    # Convert PIL to OpenCV format
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Thresholding to get binary image
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Remove horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(img, [c], -1, (255,255,255), 5)

    # Remove vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    remove_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(img, [c], -1, (255,255,255), 5)

    return img

def smart_parse(text):
    lines = text.split('\n')
    extracted = []
    for line in lines:
        # Aggressive cleaning of noise characters
        c = re.sub(r'[^a-zA-Z0-9\s]', ' ', line)
        c = " ".join(c.split())
        
        # Pattern: Look for Roll No (4 digits) + Name + Status (P/A)
        match = re.search(r'(\d{4})\s+(.+?)\s+([PpAa])(?:\s|$)', c)
        
        if match:
            roll, name, status = match.group(1), match.group(2).strip(), match.group(3).upper()
            # Remove any trailing junk after the name
            name = re.sub(r'\b(ea|nr|ee|ae|gt|fe|sp)\b', '', name, flags=re.I).strip()
            if len(name) > 2:
                extracted.append({"Roll No": roll, "Name": name, "Status": status})
    return extracted

st.title("📝 Pro Attendance Scanner")

cam_input = st.camera_input("Capture Sheet")
file_input = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

image = Image.open(cam_input) if cam_input else (Image.open(file_input) if file_input else None)

if image:
    if st.button("🚀 Generate Excel", type="primary", use_container_width=True):
        with st.spinner("Removing grid lines and extracting text..."):
            try:
                # 1. Line Removal (The secret for tables)
                no_lines_img = remove_grid_lines(image)
                
                # 2. OCR
                raw_text = pytesseract.image_to_string(no_lines_img, config='--oem 3 --psm 6')
                
                # 3. Parse
                data = smart_parse(raw_text)
                
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
                    st.error("No valid records found. Try taking the photo closer.")
                    with st.expander("Debug Raw Text"): st.text(raw_text)
            except Exception as e:
                st.error(f"Error: {e}")






