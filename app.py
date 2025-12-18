import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import cv2
import numpy as np

# SET TESSERACT PATH (CHANGE ONLY IF DIFFERENT)
import shutil
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

st.set_page_config(page_title="Attendance Scanner", layout="centered")
st.title("📸 Attendance Sheet → Excel")
st.write("Upload a photo of paper attendance sheet")

uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    h, w = img_cv.shape[:2]

    # 🔹 CROP ONLY TABLE AREA (IMPORTANT)
    crop = img_cv[int(h*0.25):int(h*0.95), int(w*0.05):int(w*0.95)]

    st.image(crop, caption="Detected Table Area", use_column_width=True)

    # 🔹 PREPROCESS IMAGE
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15, 3
    )

    # 🔹 OCR CONFIG (TABLE FRIENDLY)
    custom_config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789PA'

    text = pytesseract.image_to_string(thresh, config=custom_config)

    st.subheader("🔍 Raw OCR Output")
    st.text(text)

    # 🔹 PARSE ROWS
    rows = []
    for line in text.split("\n"):
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit():
            roll = parts[0]
            status = parts[-1]
            name = " ".join(parts[1:-1])
            rows.append([roll, name, status])

    if rows:
        df = pd.DataFrame(rows, columns=["Roll No", "Student Name", "Status (P/A)"])

        st.subheader("✅ Extracted Attendance (Editable)")
        edited_df = st.data_editor(df, use_container_width=True)

        st.download_button(
            "⬇️ Download Excel",
            edited_df.to_csv(index=False).encode("utf-8"),
            "attendance.csv",
            "text/csv"
        )
    else:
        st.warning("No valid attendance rows detected. Try a clearer image.")




