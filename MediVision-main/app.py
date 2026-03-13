from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename
import subprocess

app = Flask(__name__)

# --------------------------
# Upload Folder
# --------------------------
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --------------------------
# Load Model
# --------------------------
model = tf.keras.models.load_model("medicine_model.h5")

# Metadata for demo
metadata = {
    "paracetamol": {
        "name": "Paracetamol",
        "dosage": "500mg",
        "usage": ["Pain relief", "Fever reduction", "Cold and flu relief"],
        "side_effects": ["Rash", "Nausea", "Vomiting"],
        "benefits": ["Mild pain relief", "Fever reducer", "Easily available"],
        "summary": "Paracetamol is used for fever and mild pain."
    }
}

# --------------------------
# Prediction Function
# --------------------------
def predict_image(image_path):
    img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0

    prediction = model.predict(img_array)

    if prediction[0] > 0.5:
        return metadata["paracetamol"]
    else:
        return {"error": "Medicine not recognized"}

# --------------------------
# Flask Routes
# --------------------------
@app.route("/")
def upload_page():
    return render_template("home.html")

@app.route("/medicine")
def medicine_page():
    return render_template("medicinepage.html")

# --------------------------
# OPEN STREAMLIT APP
# --------------------------
@app.route("/run_app2", methods=["POST"])
def run_app2():
    try:
        script_path = os.path.abspath("app2.py")
        venv_python = os.path.abspath("venv/Scripts/python.exe")

        if os.name == "nt":
            command = f'start cmd /k "{venv_python} -m streamlit run {script_path}"'
        else:
            command = f"{venv_python} -m streamlit run {script_path}"

        subprocess.Popen(command, shell=True)
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# --------------------------
# LOGIN & SIGNUP
# --------------------------
users = {
    "yash@gmail.com": "123",
    "hash@gmail.com": "143"
}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email in users and users[email] == password:
            return render_template("home.html")
        else:
            return render_template("index.html", error="Invalid login")

    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email in users:
            return render_template("signup.html", error="User already exists")
        else:
            users[email] = password
            return render_template("home.html")

    return render_template("signup.html")

# ----------------------------------------------------
# 100% WORKING STATIC ROUTE TO OPEN index2.html
# ----------------------------------------------------
@app.route("/index2")
def index2():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    edi_folder = os.path.join(base_dir, "EDI_part_4")
    return send_from_directory(edi_folder, "index2.html")

# --------------------------
# UPLOAD API
# --------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"})

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    result = predict_image(filepath)
    return jsonify(result)

@app.route("/reprocess", methods=["POST"])
def reprocess():
    data = request.json
    image_name = data.get("image")

    if not image_name:
        return jsonify({"error": "No image name provided"})

    image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_name)
    result = predict_image(image_path)

    return jsonify(result)

# --------------------------
# MAIN
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
