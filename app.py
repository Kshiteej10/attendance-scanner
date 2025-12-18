import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil
import re

# --- CONFIGURATION ---
path = shutil.which("tesseract") 
if path:
    pytesseract.pytesseract.tesseract_cmd = path
else:
    # Fallback for Windows local testing
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- UI SETUP ---
st.set_page_config(page_title="Attendance Scanner", page_icon="📝")
st.title("📝 Robust Attendance Scanner")
st.write("Upload a sheet. I will extract: **Roll No + Name + Status**")

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

# --- SMART PARSING FUNCTION (FIXED) ---
def parse_attendance_text(text):
    lines = text.split('\n')
    parsed_data = []

    for line in lines:
        # 1. Clean the line (remove special symbols like | _ . -)
        clean_line = re.sub(r'[^a-zA-Z0-9\s]', '', line).strip()
        
        # 2. Skip noise
        if len(clean_line) < 4:
            continue

        # 3. Pattern Match: Number followed by Text
        # Format: "2501 Aarav Sharma P"
        match = re.match(r'(\d+)\s+([a-zA-Z\s]+)', clean_line)
        
        if match:
            roll_no = match.group(1)
            raw_text = match.group(2).strip()
            
            words = raw_text.split()
            
            # --- FIX FOR "LIST INDEX OUT OF RANGE" ---
            if not words: 
                continue # Skip if no words found after number
                
            # Logic: If last word is single letter (P/A), treat as Status
            # Otherwise, assume Status is "P" (Present)
            last_word = words[-1].upper()
            
            if len(last_word) == 1 and last_word in ['P', 'A']:
                name = " ".join(words[:-1]) # Name is everything before last letter
                status = last_word
            else:
                name = " ".join(words)      # Whole thing is name
                status = "P"                # Default to Present if P/A missing
            
            # Save valid records
            if len(name) > 2:
                parsed_data.append([roll_no, name, status])
    
    return parsed_data

# --- MAIN PROCESSING ---
if image is not None:
    st.write("---")
    st.image(image, caption="Uploaded Image", use_container_width=True)
    
    if st.button("Generate Excel ✅", type="primary"):
        with st.spinner("Processing..."):
            try:
                # 1. Image Prep
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Stronger thresholding to remove shadows
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 2. Extract Text
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(thresh, config=custom_config)

                # 3. Parse
                clean_data = parse_attendance_text(text)

                # 4. Show Result
                if clean_data:
                    st.success(f"Success! Found {len(clean_data)} students.")
                    df = pd.DataFrame(clean_data, columns=["Roll No", "Name", "Status"])
                    
                    # Editable Table
                    edited_df = st.data_editor(df, num_rows="dynamic")
                    
                    # Download CSV
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Excel", csv, "attendance.csv", "text/csv")
                else:
                    st.warning("⚠️ Could not detect valid rows. Try a clearer image.")
                    with st.expander("Debug: See what the computer saw"):
                        st.text(text)

            except Exception as e:
                st.error(f"Error: {e}")
