import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil
import re
import io

# ==========================================
# 1. PAGE CONFIGURATION (Mobile Friendly)
# ==========================================
st.set_page_config(page_title="Attendance Pro", page_icon="📱", layout="wide")

# ==========================================
# 2. TESSERACT SETUP (Cloud & Local Support)
# ==========================================
path = shutil.which("tesseract") 
if path:
    pytesseract.pytesseract.tesseract_cmd = path
else:
    # Fallback for Windows Local (Update path if needed)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ==========================================
# 3. SMART PROCESSING LOGIC
# ==========================================
def preprocess_image(image):
    """
    Cleans the image to make text sharp and removes shadows.
    """
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Adaptive Thresholding: Best for phone camera photos with uneven lighting
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return thresh

def parse_data(text):
    """
    Extracts: Roll No | Name | Status
    """
    lines = text.split('\n')
    data = []

    for line in lines:
        # A. Clean: Replace grid lines (| _ - .) with empty space
        clean_line = re.sub(r'[^a-zA-Z0-9\s]', ' ', line)
        
        # Remove extra spaces between words
        clean_line = " ".join(clean_line.split())

        # B. Skip Noise: If line is too short or just numbers
        if len(clean_line) < 5 or clean_line.isdigit():
            continue

        # C. PATTERN MATCHING
        # Pattern 1: Number ... Name ... P/A (Standard)
        match_full = re.search(r'^(\d+)\s+(.+?)\s+([PpAa])$', clean_line)
        
        # Pattern 2: Number ... Name (Missing Status -> Assume Present)
        match_partial = re.search(r'^(\d+)\s+(.+?)$', clean_line)

        roll, name, status = None, None, None

        if match_full:
            roll = match_full.group(1)
            name = match_full.group(2).strip()
            status = match_full.group(3).upper()
        elif match_partial:
            roll = match_partial.group(1)
            name = match_partial.group(2).strip()
            status = "P" # Auto-fill Present
        
        # D. FILTERING (Avoid "1", "2", "Total" etc.)
        if roll and name:
            # Name must be text, Roll must be > 0
            if len(name) > 2 and not any(char.isdigit() for char in name):
                data.append({"Roll No": int(roll), "Student Name": name, "Status": status})

    return data

# ==========================================
# 4. APP INTERFACE
# ==========================================
st.title("📱 Attendance Scanner")
st.write("Snap a photo of the list. I'll make the Excel file.")

# TAB 1: CAMERA (Default for Mobile)
cam_input = st.camera_input("Take Photo", label_visibility="visible")

# TAB 2: UPLOAD (Fallback)
file_input = None
with st.expander("Or Upload an Image File"):
    file_input = st.file_uploader("Upload", type=["jpg", "png", "jpeg"])

# SELECT IMAGE SOURCE
image = None
if cam_input:
    image = Image.open(cam_input)
elif file_input:
    image = Image.open(file_input)

# PROCESS BUTTON
if image:
    st.write("---")
    st.image(image, caption="Review Image", use_container_width=True)
    
    # Big Button for Mobile
    if st.button("Generate Excel ✅", type="primary", use_container_width=True):
        with st.spinner("⏳ Reading handwriting..."):
            try:
                # 1. Pre-process
                processed_img = preprocess_image(image)
                
                # 2. OCR Read
                # --psm 6 assumes a single uniform block of text
                raw_text = pytesseract.image_to_string(processed_img, config='--oem 3 --psm 6')
                
                # 3. Smart Parse
                structured_data = parse_data(raw_text)
                
                if structured_data:
                    # Create DataFrame
                    df = pd.DataFrame(structured_data)
                    df = df.sort_values(by="Roll No") # Sort by Roll Number
                    
                    st.success(f"🎉 Success! Found {len(df)} students.")
                    
                    # Show Data
                    st.dataframe(df, use_container_width=True)
                    
                    # 4. GENERATE EXCEL FILE
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Attendance')
                    
                    # Download Button
                    st.download_button(
                        label="📥 Download Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name="Attendance_Sheet.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("❌ No valid names found.")
                    st.info("Try holding the camera closer and steady.")
                    with st.expander("Debug Raw Text"):
                        st.text(raw_text)
                        
            except Exception as e:
                st.error(f"Error: {e}")





