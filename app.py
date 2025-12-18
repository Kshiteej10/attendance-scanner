import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import io
import re

# ==========================================
# 1. MOBILE-FIRST SETUP
# ==========================================
st.set_page_config(page_title="AI Attendance Scan", page_icon="🤖", layout="centered")

# Retrieve API Key from Streamlit Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("Please add your GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)

# FIXED: Using the standard stable model name
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    model = genai.GenerativeModel('gemini-pro-vision')

# ==========================================
# 2. UI DESIGN
# ==========================================
st.title("🤖 AI Attendance Scanner")
st.write("Snap a photo. Our AI will extract the table even with grid lines.")

cam_input = st.camera_input("Capture Sheet")
file_input = st.file_uploader("Or Upload Image", type=["jpg", "png", "jpeg"])

image_file = cam_input if cam_input else file_input

if image_file:
    img = Image.open(image_file)
    st.image(img, caption="Ready for AI Analysis", use_container_width=True)

    if st.button("🚀 Convert to Excel", type="primary", use_container_width=True):
        with st.spinner("AI is reading handwriting and fixing errors..."):
            try:
                # Optimized prompt for your specific table format
                prompt = """
                Extract the attendance data from this image. 
                Identify the table rows.
                Return ONLY a CSV-formatted list with these columns:
                Roll No, Student Name, Status
                Example format:
                2501, Aarav Sharma, P
                2502, Vivaan Singh, P
                
                Do not include markdown code blocks (like ```csv), headers, or extra text.
                """
                
                response = model.generate_content([prompt, img])
                ai_text = response.text
                
                # CLEANING THE OUTPUT
                # Remove markdown code blocks if AI included them
                clean_csv = re.sub(r'```[a-z]*\n?', '', ai_text).strip()
                
                # Read into Dataframe
                df = pd.read_csv(io.StringIO(clean_csv), names=["Roll No", "Student Name", "Status"], header=None)
                
                # Filter out header rows if AI accidentally included them
                df = df[~df['Roll No'].astype(str).str.contains("Roll", case=False)]
                
                if not df.empty:
                    st.success(f"Extracted {len(df)} records!")
                    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

                    # Excel Export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        edited_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=output.getvalue(),
                        file_name="Attendance_AI.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("AI could not find data. Please try a clearer photo.")

            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Try refreshing the page or checking your API key.")








