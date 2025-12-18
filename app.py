import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import io
import re

# ==========================================
# 1. SETUP & AUTH
# ==========================================
st.set_page_config(page_title="Attendance AI", page_icon="⚡", layout="centered")

API_KEY = st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key Not Found. Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)

# ==========================================
# 2. MODEL SELECTOR (THE FIX)
# ==========================================
st.title("⚡ Universal Attendance Scanner")
st.write("Snap a photo to extract Excel data.")

# Fetch available models dynamically
try:
    model_list = []
    for m in genai.list_models():
        # Only show models that support text/image generation
        if 'generateContent' in m.supported_generation_methods:
            model_list.append(m.name)
    
    # Sort so the best ones are at the top
    model_list.sort(key=lambda x: 'flash' not in x) # Puts 'flash' models first
    
    if not model_list:
        st.error("❌ No models found for this API Key. Check your Google AI Studio account.")
        st.stop()
        
    # User selects the model (No more guessing!)
    selected_model = st.selectbox("🤖 Select AI Model (Try the first one)", model_list)
    model = genai.GenerativeModel(selected_model)

except Exception as e:
    st.error(f"Error fetching models: {e}")
    st.stop()

# ==========================================
# 3. APP INTERFACE
# ==========================================
cam_input = st.camera_input("Take Photo")
file_input = st.file_uploader("Or Upload", type=["jpg", "png", "jpeg"])

image_file = cam_input if cam_input else file_input

if image_file:
    img = Image.open(image_file)
    st.image(img, caption="Captured", use_container_width=True)

    if st.button("🚀 Process Attendance", type="primary", use_container_width=True):
        with st.spinner(f"Processing with {selected_model}..."):
            try:
                # Prompt
                prompt = """
                Extract attendance data as a clean CSV.
                Columns: Roll No, Name, Status.
                Rules:
                1. If Status is empty, assume "P".
                2. Ignore headers/footers.
                3. Return ONLY CSV data.
                """
                
                response = model.generate_content([prompt, img])
                text = response.text
                
                # Clean Markdown
                clean_text = re.sub(r"```(csv)?", "", text).replace("```", "").strip()
                
                # Parse to DataFrame
                try:
                    df = pd.read_csv(io.StringIO(clean_text))
                except:
                    df = pd.read_csv(io.StringIO(clean_text), sep="|")

                # Show & Download
                st.success(f"Success! Found {len(df)} rows.")
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
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
                st.error("Processing Error.")
                st.info(f"Details: {e}")
                st.warning("⚠️ If this fails, try selecting a different model from the dropdown above!")











