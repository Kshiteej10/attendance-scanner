import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import io

# ==========================================
# 1. MOBILE-FIRST SETUP
# ==========================================
st.set_page_config(page_title="AI Attendance Scan", page_icon="🤖", layout="centered")

# Retrieve API Key from Streamlit Secrets (for 24/7 security)
# Note: Locally, you can replace this with your string key for testing.
API_KEY = st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("Please add your GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 2. UI DESIGN
# ==========================================
st.title("🤖 AI Attendance Scanner")
st.write("Snap a photo. Our AI will handle the handwriting and grid lines.")

# Native Mobile Camera & Upload
cam_input = st.camera_input("Capture Sheet")
file_input = st.file_uploader("Or Upload Image", type=["jpg", "png", "jpeg"])

image_file = cam_input if cam_input else file_input

if image_file:
    img = Image.open(image_file)
    st.image(img, caption="Ready for AI Analysis", use_container_width=True)

    if st.button("🚀 Convert to Excel", type="primary", use_container_width=True):
        with st.spinner("AI is reading handwriting..."):
            try:
                # Use Gemini to extract data
                prompt = """
                Act as a data entry expert. Read this attendance sheet image.
                Extract every row into a table with exactly 3 columns:
                1. Roll No (as a number)
                2. Student Name
                3. Status (P or A)
                Only return the data rows. No conversational text.
                """
                
                response = model.generate_content([prompt, img])
                ai_text = response.text
                
                # Convert AI response to Dataframe
                # We assume AI returns a markdown table or CSV-like text
                from io import StringIO
                
                # Clean up AI output if it includes markdown table markers
                clean_text = ai_text.replace('```csv', '').replace('```', '').strip()
                
                # Split lines and create list of lists
                rows = [line.split('|') for line in clean_text.split('\n') if '|' in line]
                
                if not rows: # Fallback if AI didn't use |
                    st.warning("AI output format varied. Attempting to fix...")
                    st.text(ai_text)
                    st.stop()

                # Clean headers out of the row data
                data_rows = []
                for r in rows:
                    clean_row = [cell.strip() for cell in r if cell.strip()]
                    if len(clean_row) >= 3 and not any("Roll" in str(x) for x in clean_row):
                        data_rows.append(clean_row[:3])

                df = pd.DataFrame(data_rows, columns=["Roll No", "Student Name", "Status"])
                
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

            except Exception as e:
                st.error(f"AI Error: {e}")







