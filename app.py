import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import io
import re

# ==========================================
# 1. SETUP & AUTH
# ==========================================
st.set_page_config(page_title="AI Attendance", page_icon="✅", layout="centered")

# Get API Key
API_KEY = st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key Missing. Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)

# ==========================================
# 2. AUTO-DETECT WORKING MODEL
# ==========================================
@st.cache_resource
def get_working_model():
    """
    Asks Google: 'What models are available to me?'
    Returns the best one that supports vision (images).
    """
    try:
        # Priority list of models to try
        priority_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro-vision', 'gemini-pro']
        
        # Get list of ALL available models for this key
        available_models = [m.name for m in genai.list_models()]
        
        # Find the first match
        for p_model in priority_models:
            # Check if the priority model exists in the available list (e.g., 'models/gemini-1.5-flash')
            for a_model in available_models:
                if p_model in a_model:
                    return genai.GenerativeModel(a_model)
        
        # If no match found, default to generic 'gemini-pro' and hope for the best
        return genai.GenerativeModel('gemini-pro')
        
    except Exception as e:
        # Fallback if list_models fails
        return genai.GenerativeModel('gemini-pro')

# Load the model once
model = get_working_model()

# ==========================================
# 3. APP INTERFACE
# ==========================================
st.title("✅ AI Attendance Scanner")
st.success(f"System Ready. Using AI Model.")

cam_input = st.camera_input("Take Photo of Sheet")
file_input = st.file_uploader("Or Upload Image", type=["jpg", "png", "jpeg"])

image_file = cam_input if cam_input else file_input

if image_file:
    img = Image.open(image_file)
    st.image(img, caption="Image Captured", use_container_width=True)

    if st.button("🚀 Process Attendance", type="primary", use_container_width=True):
        with st.spinner("Reading document..."):
            try:
                # Prompt: Ask for pure CSV data
                prompt = """
                You are a data entry assistant.
                Look at this attendance sheet.
                Output the data strictly as a CSV format.
                Columns: Roll No, Name, Status.
                Rules:
                1. Ignore headers like "Department", "Date", etc.
                2. If Status is empty or missing, assume "P".
                3. Do NOT write sentences. Only CSV data.
                """
                
                # Generate
                response = model.generate_content([prompt, img])
                text_out = response.text
                
                # Cleanup: Remove Markdown (```csv ... ```)
                clean_text = re.sub(r"```(csv)?", "", text_out).replace("```", "").strip()
                
                # Convert to DataFrame
                # We use specific separator logic to handle different AI outputs
                try:
                    df = pd.read_csv(io.StringIO(clean_text))
                except:
                    # Fallback: if comma fails, try pipe |
                    df = pd.read_csv(io.StringIO(clean_text), sep="|")

                # Basic Cleanup of Columns
                # Rename columns to standard names if they differ
                df.columns = [c.strip() for c in df.columns]
                
                # Display
                st.write("### Extracted Data")
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                # Download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=output.getvalue(),
                    file_name="Attendance.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Processing Error: {str(e)}")
                st.info("Tip: Ensure the photo is clear and contains text.")









