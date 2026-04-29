from flask import Flask, render_template, session, request, redirect, url_for, jsonify
import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
from werkzeug.security import check_password_hash, generate_password_hash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "parking_secret_key"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# buat folder jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
# ========================
# KONEKSI DATABASE
# ========================
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="",
    db="campus_parking"
)

# ========================
# FUNGSI LOG PARKIR
# ========================
def log_kendaraan(jenis, area, status, plat):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO logs_parkir (jenis_kendaraan, area, status, plat) VALUES (%s,%s,%s,%s)",
        (jenis, area, status, plat)
    )
    db.commit()

# ========================
# BUAT USER DEFAULT
# ========================
# ========================
# BUAT USER DEFAULT (AUTO)
# ========================
def create_default_user():
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users WHERE email=%s", ("admin@gmail.com",))
    user = cursor.fetchone()

    if not user:
        password_hash = generate_password_hash("admin123")

        cursor.execute("""
            INSERT INTO users (nama, nim, fakultas, nohp, email, password, role)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            "Admin",
            "000000",
            "Admin",
            "08123456789",
            "admin@gmail.com",
            password_hash,
            "admin"
        ))

        db.commit()

create_default_user()

# ========================
# LOGIN PAGE
# ========================
@app.route('/')
def login():
    return render_template('login.html')

# ========================
# PROSES LOGIN
# ========================
@app.route('/login', methods=['POST'])
def do_login():
    email = request.form['email']
    password = request.form['password']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password'], password):
        session['login'] = True
        session['nama'] = user['nama']
        session['email'] = user['email']
        session['role'] = user['role']

        return redirect('/dashboard')

    return "Login gagal, email/password salah"

# ========================
# REGISTER
# ========================
@app.route('/do_register', methods=['POST'])
def do_register():
    nama = request.form['nama']
    nim = request.form['nim']
    fakultas = request.form['fakultas']
    nohp = request.form['nohp']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # 🔥 CEK EMAIL SUDAH ADA ATAU BELUM
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    cek = cursor.fetchone()

    if cek:
        return "Email sudah terdaftar!"

    # 🔥 JIKA BELUM ADA → SIMPAN
    cursor.execute("""
        INSERT INTO users (nama, nim, fakultas, nohp, email, password, role)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (nama, nim, fakultas, nohp, email, password, 'user'))

    db.commit()

    return redirect('/')
# ========================
# REGISTER PAGE
# ========================
@app.route('/register')
def register():
    return render_template('register.html')
# ========================
# DASHBOARD
# ========================
@app.route('/dashboard')
def dashboard():
    if 'login' in session:
        if session['role'] == 'admin':
            return render_template('dashboard_admin.html')
        else:
            return render_template('dashboard_user.html')
    return redirect('/')

# ========================
# LIHAT AREA
# ========================
@app.route('/lihat_area')
def lihat_area():
    return render_template('lihat_area.html')

# ========================
# LAPOR PARKIR LIAR
# ========================
@app.route('/lapor_parkir_liar', methods=['GET', 'POST'])
def lapor():
    if request.method == 'POST':
        area = request.form['area']
        plat = request.form['plat']
        keterangan = request.form['keterangan']

        # FOTO
        foto = request.files['foto']
        nama_file = foto.filename
        foto.save('static/uploads/' + nama_file)

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO laporan (area, plat, keterangan, foto, status) VALUES (%s,%s,%s,%s,%s)",
            (area, plat, keterangan, nama_file, "Belum Dibaca")
        )
        db.commit()

        return redirect('/dashboard')

    return render_template('lapor_parkir_liar.html')

# ========================
# PROFIL
# ========================
@app.route('/profil')
def profil():
    return render_template('profil.html')

# ========================
# LOGS
# ========================
@app.route('/logs')
def logs():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM logs_parkir ORDER BY waktu DESC")
    data = cursor.fetchall()
    return render_template('logs.html', logs=data)

# ========================
# KELOLA AREA (ADMIN)
# ========================
@app.route('/admin/kelola_area')
def kelola_area():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM area_parkir")
    data = cursor.fetchall()
    return render_template('admin_kelola_area.html', data=data)

# ========================
# UPDATE AREA + LOG
# ========================
@app.route('/admin/update_area/<int:id>')
def update_area(id):
    cursor = db.cursor()

    cursor.execute("SELECT nama_area, status FROM area_parkir WHERE id=%s", (id,))
    area = cursor.fetchone()

    nama_area = area[0]
    status = area[1]

    if status == 'Tersedia':
        new_status = 'Penuh'
        jenis = "Mobil"
        plat = "BG" + str(id) + "123XX"
        log_kendaraan(jenis, nama_area, "Masuk", plat)

    else:
        new_status = 'Tersedia'
        jenis = "Motor"
        plat = "BG" + str(id) + "321YY"
        log_kendaraan(jenis, nama_area, "Keluar", plat)

    cursor.execute(
        "UPDATE area_parkir SET status=%s WHERE id=%s",
        (new_status, id)
    )
    db.commit()

    return redirect('/admin/kelola_area')

# ========================
# ADMIN LAPORAN
# ========================
@app.route('/admin/laporan')
def admin_laporan():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM laporan")
    data = cursor.fetchall()
    return render_template('admin_laporan.html', data=data)

# ========================
# API REALTIME
# ========================
@app.route('/api/area')
def api_area():
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM area_parkir")
    area = cursor.fetchall()

    data = []
    for a in area:
        data.append({
            'nama': a['nama_area'],
            'status': a['status']
        })

    return jsonify(data)

# ========================
# PETA
# ========================
@app.route('/peta')
def peta():
    return render_template('peta.html')

# ========================
# LOGOUT
# ========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ========================
# RUN
# ========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)