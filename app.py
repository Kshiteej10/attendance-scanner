import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import io
import re

# ==========================================
# 1. SETUP
# ==========================================
st.set_page_config(page_title="Attendance AI", page_icon="⚡", layout="centered")

API_KEY = st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key Not Found. Please add it to Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)

# ==========================================
# 2. FORCE SPECIFIC FREE MODELS
# ==========================================
def get_model():
    # We explicitly try the FREE models in order.
    # We do NOT ask the server for a list (to avoid picking restricted models).
    models_to_try = [
        'gemini-1.5-flash',          # Best & Free
        'gemini-1.5-flash-latest',   # Alternate name
        'gemini-pro-vision',         # Old Reliable
        'models/gemini-1.5-flash'    # Full path fallback
    ]
    
    for model_name in models_to_try:
        try:
            # Try to initialize
            model = genai.GenerativeModel(model_name)
            # Dry run to see if it exists (doesn't consume quota)
            return model
        except:
            continue
            
    # Final fallback
    return genai.GenerativeModel('gemini-pro')

model = get_model()

# ==========================================
# 3. APP INTERFACE
# ==========================================
st.title("⚡ Attendance Scanner")
st.write("Using AI Model: " + str(model.model_name).replace("models/", ""))

# Camera & Upload
cam_input = st.camera_input("Take Photo")
file_input = st.file_uploader("Or Upload", type=["jpg", "png", "jpeg"])

image_file = cam_input if cam_input else file_input

if image_file:
    img = Image.open(image_file)
    st.image(img, caption="Captured", use_container_width=True)

    if st.button("🚀 Process Attendance", type="primary", use_container_width=True):
        with st.spinner("AI is processing (this is free)..."):
            try:
                # Prompt optimized for Gemini Flash
                prompt = """
                You are a data entry machine. 
                Look at this attendance sheet. 
                Output ONLY a CSV table with 3 columns: Roll No, Name, Status.
                
                Rules:
                1. If Status is marked "P" or present, write "P".
                2. If Status is marked "A" or absent, write "A".
                3. If Status is blank, write "P".
                4. Do NOT use markdown. Do NOT write sentences.
                """
                
                response = model.generate_content([prompt, img])
                text = response.text
                
                # Clean Markdown
                clean_text = re.sub(r"```(csv)?", "", text).replace("```", "").strip()
                
                # Parse
                try:
                    df = pd.read_csv(io.StringIO(clean_text))
                except:
                    df = pd.read_csv(io.StringIO(clean_text), sep="|")

                # Show
                st.success(f"Found {len(df)} students")
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                # Download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, index=False)
                
                st.download_button(
                    "📥 Download Excel",
                    output.getvalue(),
                    "Attendance.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            except Exception as e:
                st.error("Processing Error. Please try again.")
                st.info(f"Details: {e}")










