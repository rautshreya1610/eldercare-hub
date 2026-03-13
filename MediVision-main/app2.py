import streamlit as st
from PIL import Image
import pytesseract
import io
import tensorflow as tf
import numpy as np
import cv2
import os

# -------------------------------------------------------
# 🔧 FIXED: FINAL TESSERACT PATHS
# -------------------------------------------------------
# Based on your system output:
# C:\Program Files\Tesseract-OCR\tesseract.exe\tesseract.exe

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe\tesseract.exe"
TESSDATA_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe\tessdata"

if not os.path.exists(TESSERACT_PATH):
    st.error(f"Tesseract NOT FOUND at:\n{TESSERACT_PATH}")
else:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    os.environ["TESSDATA_PREFIX"] = TESSDATA_PATH


# -------------------------------------------------------
# STREAMLIT PAGE CONFIG + UI STYLING
# -------------------------------------------------------
st.set_page_config(page_title="Prescription Recognition", layout="wide")

st.markdown("""
<h1 style='text-align:center; font-size:40px; color:#6c5ce7;'>
Revolutionizing Handwritten Prescription Recognition (CNN + OCR)
</h1>
""", unsafe_allow_html=True)


# -------------------------------------------------------
# LOAD MODEL
# -------------------------------------------------------
@st.cache_resource
def load_model():
    return tf.keras.models.load_model("model_saved.keras")

model = load_model()


# -------------------------------------------------------
# CNN PREPROCESS
# -------------------------------------------------------
def preprocess_image(image, target_size=(28, 28)):
    try:
        if image.mode != "L":
            image = image.convert("L")
        image = image.resize(target_size)

        img = np.array(image, dtype=np.float32) / 255.0
        img = np.expand_dims(img, axis=-1)
        img = np.expand_dims(img, axis=0)
        return img
    except Exception as e:
        st.error(f"Preprocess Error: {e}")
        return None


# -------------------------------------------------------
# OCR ENHANCEMENT
# -------------------------------------------------------
def enhance_for_ocr(image):
    try:
        img = np.array(image)

        if len(img.shape) == 2:
            gray = img
        elif img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        elif img.shape[2] == 4:
            rgb = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        else:
            st.error("Unsupported image format")
            return None

        # Denoise + Threshold + Upscale
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        th = cv2.resize(th, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

        return Image.fromarray(th)

    except Exception as e:
        st.error(f"OCR Enhancement Error: {e}")
        return None


# -------------------------------------------------------
# OCR EXTRACTION
# -------------------------------------------------------
def extract_text(image):
    enhanced = enhance_for_ocr(image)
    if enhanced is None:
        return "", 0

    try:
        config = r"--oem 3 --psm 6"

        data = pytesseract.image_to_data(
            enhanced,
            config=config,
            output_type=pytesseract.Output.DICT
        )

        words, confs = [], []

        for i in range(len(data["text"])):
            txt = data["text"][i].strip()
            conf = data["conf"][i]

            if not txt:
                continue

            try:
                conf = float(conf)
            except:
                continue

            if conf > 0:
                words.append(txt)
                confs.append(conf)

        text = " ".join(words)
        avg_conf = np.mean(confs) if confs else 0
        return text, avg_conf

    except Exception as e:
        st.error(f"OCR Error: {e}")
        return "", 0


# -------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------
st.sidebar.header("Options")

if "camera_on" not in st.session_state:
    st.session_state["camera_on"] = False

if st.sidebar.button("Camera ON"):
    st.session_state["camera_on"] = True

if st.sidebar.button("Camera OFF"):
    st.session_state["camera_on"] = False


# -------------------------------------------------------
# MAIN INTERFACE
# -------------------------------------------------------
st.markdown("<div style='padding:20px; background:white; border-radius:15px;'>",
            unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Prescription Image", type=["png", "jpg", "jpeg"])

captured = None
if st.session_state["camera_on"]:
    captured = st.camera_input("Capture Image")

image = None
if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Uploaded Image", use_container_width=True)

if captured:
    image = Image.open(io.BytesIO(captured.getvalue()))
    st.image(image, caption="Captured Image", use_container_width=True)


# -------------------------------------------------------
# PROCESSING BUTTON
# -------------------------------------------------------
if st.button("Start Prediction + OCR"):
    if image is None:
        st.warning("Please upload or capture an image first.")
    else:
        with st.spinner("Processing... Please wait..."):

            # CNN Prediction
            model_input = preprocess_image(image)
            pred = model.predict(model_input)
            pred_class = np.argmax(pred)
            pred_conf = np.max(pred) * 100

            st.subheader("🔮 CNN Model Prediction:")
            st.write(f"Predicted Class: **{pred_class}**")
            st.write(f"Prediction Confidence: **{pred_conf:.2f}%**")

            # OCR Extraction
            text, ocr_conf = extract_text(image)

            st.subheader("📄 Extracted Text (OCR):")
            if len(text.strip()) == 0:
                st.error("No readable text detected.")
            else:
                st.success(f"OCR Confidence: {ocr_conf:.2f}%")
                st.text_area("Extracted Text", text, height=200)


# -------------------------------------------------------
# CLEAR BUTTON
# -------------------------------------------------------
if st.button("Clear"):
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
