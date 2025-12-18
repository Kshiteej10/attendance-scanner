import streamlit as st
import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import shutil
import re  # New tool for pattern matching

# --- CONFIGURATION ---
path = shutil.which("tesseract") 
if path:
    pytesseract.pytesseract.tesseract_cmd = path
else:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- UI SETUP ---
st.set_page_config(page_title="Attendance Scanner", page_icon="📝")
st.title("📝 Smart Attendance Scanner")
st.write("Upload a sheet. I will try to find: **Roll No + Name + Status**")

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

# --- SMART PARSING FUNCTION ---
def parse_attendance_text(text):
    """
    Looks for lines that contain a Number (Roll No) and Text (Name).
    Ignores headers and random noise.
    """
    lines = text.split('\n')
    parsed_data = []

    for line in lines:
        # 1. Clean the line (remove special symbols like | _ . -)
        clean_line = re.sub(r'[^a-zA-Z0-9\s]', '', line).strip()
        
        # 2. Skip if line is too short (likely noise)
        if len(clean_line) < 5:
            continue

        # 3. PATTERN MATCHING: Look for a number at the start
        # This finds "2501" followed by "Aarav..."
        match = re.match(r'(\d+)\s+([a-zA-Z\s]+)', clean_line)
        
        if match:
            roll_no = match.group(1)
            rest_of_text = match.group(2).strip()
            
            # Simple logic: The last letter is likely Status (P/A)
            # If the last word is P or A, take it. Otherwise assume Present.
            words = rest_of_text.split()
            name = " ".join(words[:-1]) # Name is everything except last word
            status = words[-1].upper()  # Last word is status
            
            # Safety check: If Name is empty, something went wrong
            if len(name) > 2:
                parsed_data.append([roll_no, name, status])
    
    return parsed_data

# --- PROCESSING ---
if image is not None:
    st.write("---")
    st.image(image, caption="Selected Image", use_container_width=True)
    
    if st.button("Generate Excel ✅", type="primary"):
        with st.spinner("🧠 Analyzing patterns..."):
            try:
                # 1. Image Prep (Standard)
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Apply threshold to clean up shadows
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 2. Extract Text
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(thresh, config=custom_config)

                # 3. Run Smart Parser
                clean_data = parse_attendance_text(text)

                # 4. Show & Download
                if clean_data:
                    st.success(f"Found {len(clean_data)} student records!")
                    
                    # Create a proper DataFrame with Columns
                    df = pd.DataFrame(clean_data, columns=["Roll No", "Name", "Status"])
                    
                    # Editable Table
                    edited_df = st.data_editor(df, num_rows="dynamic")
                    
                    # Download
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Clean Excel",
                        data=csv,
                        file_name='attendance_clean.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("⚠️ Text detected, but I couldn't find Roll Numbers. Try a clearer photo.")
                    with st.expander("See Raw Text (Debug)"):
                        st.text(text)
                    
            except Exception as e:
                st.error(f"Error: {e}")
