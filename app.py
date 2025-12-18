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
# 1. ENVIRONMENT CONFIGURATION
# ==========================================
# Automatically detect Tesseract on Cloud (Linux) or Local (Windows)
path = shutil.which("tesseract") 
if path:
    pytesseract.pytesseract.tesseract_cmd = path
else:
    # Common Windows default path
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ==========================================
# 2. CORE LOGIC: THE INTELLIGENT PARSER
# ==========================================
def preprocess_image(image):
    """
    Converts image to high-contrast black & white to remove shadows and grid lines.
    """
    img_array = np.array(image)
    
    # Convert to Grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Adaptive Thresholding (Better for varying lighting conditions)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return thresh

def parse_data_smart(text):
    """
    Scans text line-by-line using Regex Patterns.
    """
    lines = text.split('\n')
    extracted_data = []

    for line in lines:
        # A. Clean the line: Replace | _ - . with spaces
        clean_line = re.sub(r'[^a-zA-Z0-9\s]', ' ', line)
        clean_line = " ".join(clean_line.split()) # Remove extra spaces

        # B. SKIP NOISE: If line is too short or just numbers, skip it
        if len(clean_line) < 5 or clean_line.isdigit():
            continue

        # C. PATTERN MATCHING ENGINE
        
        # Pattern 1: Roll No + Name + Status (P/A)
        # Example: "2501 Amit Sharma P"
        match_full = re.search(r'^(\d+)\s+(.+?)\s+([PpAa])$', clean_line)
        
        # Pattern 2: Roll No + Name (Missing Status) -> Default to Present
        # Example: "2502 Priya Singh" (OCR missed the 'P')
        match_partial = re.search(r'^(\d+)\s+(.+?)$', clean_line)

        roll, name, status = None, None, None

        if match_full:
            roll = match_full.group(1)
            name = match_full.group(2).strip()
            status = match_full.group(3).upper()
        elif match_partial:
            roll = match_partial.group(1)
            name = match_partial.group(2).strip()
            status = "P" # Default Assumption
        
        # D. VALIDATION GATE
        # Only save if Name has no numbers and is reasonably long
        if roll and name and len(name) > 2 and not any(char.isdigit() for char in name):
            extracted_data.append({"Roll No": int(roll), "Student Name": name, "Status": status})

    return extracted_data

# ==========================================
# 3. USER INTERFACE (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Attendance Architect", page_icon="🏗️", layout="centered")

st.markdown("""
    <h1 style='text-align: center; color: #0e1117;'>Attendance Architect</h1>
    <p style='text-align: center;'>Professional Optical Character Recognition (OCR) System</p>
    <hr>
""", unsafe_allow_html=True)

# Input Tabs
tab1, tab2 = st.tabs(["📸 Camera Scan", "📂 Upload File"])

image = None

with tab1:
    cam_input = st.camera_input("Capture Sheet")
    if cam_input: image = Image.open(cam_input)

with tab2:
    file_input = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    if file_input: image = Image.open(file_input)

if image:
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.image(image, caption="Original Source", use_container_width=True)
    
    with col2:
        st.info("ℹ️ **System Status:** Ready to process.\nClick button below to start extraction engine.")

    if st.button("🚀 Run Extraction Engine", type="primary"):
        with st.spinner("Processing image pixels..."):
            try:
                # 1. Preprocess
                processed_img = preprocess_image(image)
                
                # 2. Extract Text
                # psm 6 assumes a single uniform block of text
                raw_text = pytesseract.image_to_string(processed_img, config='--oem 3 --psm 6')
                
                # 3. Parse Data
                structured_data = parse_data_smart(raw_text)
                
                if structured_data:
                    df = pd.DataFrame(structured_data)
                    
                    # Sort by Roll No
                    df = df.sort_values(by="Roll No")
                    
                    st.success(f"✅ Extraction Complete! Found {len(df)} records.")
                    
                    # Show Editable Dataframe
                    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                    
                    # 4. EXCEL EXPORT (The "Pro" feature)
                    # We write to a memory buffer so we don't need to save a file on the server
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        edited_df.to_excel(writer, index=False, sheet_name='Attendance')
                    
                    st.download_button(
                        label="📥 Download as Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name="Attendance_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("❌ No valid data pattern found.")
                    st.warning("Diagnostic: The AI saw this text (check for garbage):")
                    st.code(raw_text)
                    
            except Exception as e:
                st.error(f"System Error: {str(e)}")

