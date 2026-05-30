from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import numpy as np
# from tensorflow.keras.models import load_model   # décommenter quand modèle dispo
# from tensorflow.keras.preprocessing import image  # décommenter quand modèle dispo
import os
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'skinai_secret_key_2025'

# ── CONFIGURATION DES UPLOADS ───────────────────
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Créer le dossier s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ── MODÈLE ──────────────────────────────────────
# model = load_model('model/vgg16_skin_cancer.h5')  # décommenter quand modèle dispo
model = None  # simulation temporaire

# ── BASE DE DONNÉES ─────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skin_cancer_db"
    )

# ── STATS DASHBOARD ─────────────────────────────
def get_stats():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM patients")
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as n FROM patients WHERE result='Malin'")
        malin = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) as n FROM patients WHERE result='Bénin'")
        benin = cursor.fetchone()['n']
        db.close()
        return {'total': total, 'malin': malin, 'benin': benin}
    except:
        return {'total': 0, 'malin': 0, 'benin': 0}

# ════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('login'))

# ── LOGIN ────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        db.close()
        if user:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects !', 'danger')
    return render_template('login.html')

# ── LOGOUT ───────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── DASHBOARD ────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)

# ── PREDICT ──────────────────────────────────────
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name     = request.form['name']
        age      = request.form['age']
        img_file = request.files['image']

        if img_file:
            # Sécuriser le nom du fichier et construire le chemin
            filename = secure_filename(img_file.filename)
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Sauvegarder l'image
            img_file.save(img_path)

            if model is not None:
                # ── Vrai modèle VGG16 ──
                from tensorflow.keras.preprocessing import image as keras_image
                img = keras_image.load_img(img_path, target_size=(224, 224))
                img_array = keras_image.img_to_array(img) / 255.0
                img_array = np.expand_dims(img_array, axis=0)
                prediction = model.predict(img_array)
                prob   = float(prediction[0][0])
                result = 'Malin' if prob > 0.5 else 'Bénin'
            else:
                # ── Simulation temporaire ──
                prob   = random.uniform(0.15, 0.95)
                result = 'Malin' if prob > 0.5 else 'Bénin'

            # Enregistrer en base
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO patients (name, age, result, probability, image_path) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (name, age, result, prob, img_path)
                )
                db.commit()
                db.close()
            except Exception as e:
                flash(f"Erreur lors de l'enregistrement en base : {str(e)}", 'danger')
                return redirect(url_for('predict'))

            return render_template('result.html',
                                   result=result,
                                   prob=round(prob * 100, 1),
                                   img=img_path)

    return render_template('predict.html')

# ── PATIENTS ─────────────────────────────────────
@app.route('/patients')
def patients():
    if 'user' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients ORDER BY created_at DESC")
    all_patients = cursor.fetchall()
    db.close()
    return render_template('patients.html', patients=all_patients)

# ════════════════════════════════════════════════
if __name__ == '__main__':
    app.run(debug=True)
