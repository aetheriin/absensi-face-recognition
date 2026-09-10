import os   
import uuid
import json
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash
from utils.auth import User
from PIL import Image
from flask import Flask, request, jsonify, render_template, redirect
from datetime import time, timedelta, datetime, date as date_cls
from utils.face_utils import extract_embedding, embedding_to_binary, binary_to_embedding, compare_faces
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from utils.db_utils import (
    insert_karyawan,
    get_all_karyawan,
    get_daftar_karyawan,
    get_karyawan_by_id,
    update_karyawan,
    delete_karyawan,
    get_absensi_hari_ini,
    insert_jam_masuk,
    update_jam_keluar,
    get_connection,
    get_laporan_by_tanggal,
    set_status_manual,
    cek_nik_sudah_ada,
    cari_wajah_mirip,
    get_dashboard_summary, 
    get_tren_7_hari,
    get_user_by_username, 
    update_last_login, 
    insert_user
)

JAM_MASUK_STANDAR = time(8, 0)

app = Flask(__name__)
app.secret_key = "ganti-dengan-random-string-yang-panjang-dan-rahasia"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        row = get_user_by_username(username)
        if row is None or not check_password_hash(row.PasswordHash, password):
            return render_template("login.html", error="Username atau password salah")

        user = User(row.Id, row.Username, row.NamaLengkap, row.Role)
        login_user(user)
        update_last_login(row.Id)
        return redirect("/dashboard")

    return render_template("login.html", error=None)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")
UPLOAD_FOLDER = "static/uploads"

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def ekstensi_diizinkan(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def simpan_gambar_aman(file, upload_folder):
    if file.filename == '':
        return None, "Nama file kosong"

    if not ekstensi_diizinkan(file.filename):
        return None, "Ekstensi file tidak diizinkan (hanya .jpg, .jpeg, .png)"

    filename_aman = secure_filename(file.filename)
    ext = filename_aman.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, unique_filename)

    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(filepath, format='JPEG' if ext in ('jpg', 'jpeg') else 'PNG')
    except Exception as e:
        return None, f"File bukan gambar valid: {str(e)}"

    return filepath, unique_filename

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/daftar-absen")
def daftar_absen():
    return render_template("index.html", active_page="daftar-absen")

@app.route("/dashboard")
@login_required
def dashboard():
    tanggal = date_cls.today()
    summary = get_dashboard_summary(tanggal)
    tren = get_tren_7_hari(tanggal)
    labels = [item["tanggal"] for item in tren]
    values = [item["hadir"] for item in tren]
    return render_template("dashboard.html", summary=summary, labels=json.dumps(labels), values=json.dumps(values), active_page="dashboard")

@app.route("/laporan")
@login_required
def laporan():
    tanggal_str = request.args.get("tanggal")
    if tanggal_str:
        tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
    else:
        tanggal = date_cls.today()

    rows = get_laporan_by_tanggal(tanggal)
    data = []
    for row in rows:
        if row["Status"] in ("Izin", "Sakit", "Cuti"):
            row["status_masuk"] = row["Status"]
            row["telat_menit"] = 0
        elif row["JamMasuk"]:
            status = hitung_status_absensi(tanggal, row["JamMasuk"])
            row.update(status)
        else:
            row["status_masuk"] = "Belum Ada Data"
            row["telat_menit"] = 0
        data.append(row)

    return render_template("laporan.html", data=data, tanggal=tanggal, active_page="laporan")

@app.route("/laporan/edit-status", methods=["POST"])
@login_required
def edit_status_laporan():
    karyawan_id = request.form.get("karyawan_id")
    tanggal = request.form.get("tanggal")
    status = request.form.get("status")
    keterangan = request.form.get("keterangan")
    set_status_manual(karyawan_id, tanggal, status, keterangan)
    return redirect(f"/laporan?tanggal={tanggal}")

@app.route("/karyawan")
@login_required
def karyawan():
    data = get_daftar_karyawan()
    return render_template("karyawan.html", data=data, active_page="karyawan")

@app.route("/karyawan/edit/<int:karyawan_id>", methods=["POST"])
@login_required
def edit_karyawan(karyawan_id):
    nama = request.form.get("nama", "").strip()
    nik = request.form.get("nik", "").strip()
    file = request.files.get("foto")

    if not nama:
        return jsonify({"error": "Nama tidak boleh kosong"}), 400
    if nik and not nik.isdigit():
        return jsonify({"error": "NIK harus berupa angka"}), 400
    if nik and cek_nik_sudah_ada(nik, exclude_id=karyawan_id):
        return jsonify({"error": f"NIK '{nik}' sudah dipakai karyawan lain"}), 400

    embedding_binary = None
    foto_path = None
    if file and file.filename != "":
        filepath, hasil = simpan_gambar_aman(file, UPLOAD_FOLDER)
        if filepath is None:
            return jsonify({"error": hasil}), 400

        embedding_baru = extract_embedding(filepath)
        if embedding_baru is None:
            return jsonify({"error": "Wajah tidak terdeteksi di foto baru"}), 400

        wajah_mirip = cari_wajah_mirip(embedding_baru, exclude_id=karyawan_id)
        if wajah_mirip:
            _, nama_terdaftar = wajah_mirip
            return jsonify({"error": f"Wajah ini sudah terdaftar sebagai '{nama_terdaftar}'"}), 400

        embedding_binary = embedding_to_binary(embedding_baru)
        foto_path = f"uploads/{hasil}"

    update_karyawan(karyawan_id, nama, nik if nik else None, embedding_binary, foto_path)
    return jsonify({"message": f"Data '{nama}' berhasil diperbarui"}), 200

@app.route("/karyawan/hapus/<int:karyawan_id>", methods=["POST"])
@login_required
def hapus_karyawan(karyawan_id):
    delete_karyawan(karyawan_id)
    return redirect("/karyawan")

@app.route("/register", methods=["POST"])
def register():
    nama = request.form.get("nama", "").strip()
    nik = request.form.get("nik", "").strip()
    file = request.files.get("foto")

    if not nama:
        return jsonify({"error": "Nama tidak boleh kosong"}), 400
    if not file:
        return jsonify({"error": "Foto wajib diisi"}), 400
    if not nik:
        return jsonify({"error": "NIK wajib diisi"}), 400
    if not nik.isdigit():
        return jsonify({"error": "NIK harus berupa angka"}), 400
    if cek_nik_sudah_ada(nik):
        return jsonify({"error": f"NIK '{nik}' sudah terdaftar untuk karyawan lain"}), 400

    filepath, hasil = simpan_gambar_aman(file, UPLOAD_FOLDER)
    if filepath is None:
        return jsonify({"error": hasil}), 400

    embedding = extract_embedding(filepath)
    if embedding is None:
        return jsonify({"error": "Wajah tidak terdeteksi di foto"}), 400

    wajah_mirip = cari_wajah_mirip(embedding)
    if wajah_mirip:
        karyawan_id, nama_terdaftar = wajah_mirip
        return jsonify({"error": f"Wajah ini sudah terdaftar sebagai '{nama_terdaftar}'"}), 400

    binary_data = embedding_to_binary(embedding)
    insert_karyawan(nama, binary_data, foto_path=f"uploads/{hasil}", nik=nik)

    return jsonify({"message": f"Karyawan '{nama}' berhasil didaftarkan"}), 200

@app.route("/absen", methods=["POST"])
def absen():
    file = request.files.get("foto")
    if not file:
        return jsonify({"error": "Foto wajib diisi"}), 400

    filepath, hasil = simpan_gambar_aman(file, UPLOAD_FOLDER)
    if filepath is None:
        return jsonify({"error": hasil}), 400

    embedding_baru = extract_embedding(filepath)
    if embedding_baru is None:
        return jsonify({"error": "Wajah tidak terdeteksi di foto"}), 400

    karyawan_list = get_all_karyawan()
    match_found = None

    for row in karyawan_list:
        karyawan_id, nama, embedding_binary = row
        embedding_tersimpan = binary_to_embedding(embedding_binary)
        is_match, distance = compare_faces(embedding_tersimpan, embedding_baru)
        if is_match:
            match_found = (karyawan_id, nama)
            break

    if not match_found:
        return jsonify({"error": "Wajah tidak dikenali"}), 404

    karyawan_id, nama = match_found
    nik_row = get_karyawan_by_id(karyawan_id)
    nik = nik_row.NIK if nik_row and nik_row.NIK else "-"

    absensi_row = get_absensi_hari_ini(karyawan_id)

    if absensi_row is None:
        insert_jam_masuk(karyawan_id)
        status = "Masuk"
    elif absensi_row.JamKeluar is None:
        update_jam_keluar(absensi_row.Id)
        status = "Keluar"
    else:
        return jsonify({"message": f"{nama} sudah absen masuk & keluar hari ini"}), 200

    return jsonify({
        "message": f"{nama} berhasil absen {status.lower()}",
        "nama": nama,
        "nik": nik,
        "status": status
    }), 200

def hitung_status_absensi(tanggal, jam_masuk):
    hasil = {"status_masuk": "-", "telat_menit": 0}

    if jam_masuk:
        selisih_masuk = (datetime.combine(tanggal, jam_masuk) - datetime.combine(tanggal, JAM_MASUK_STANDAR)).total_seconds() / 60
        if selisih_masuk > 0:
            hasil["status_masuk"] = "Telat"
            hasil["telat_menit"] = round(selisih_masuk)
        else:
            hasil["status_masuk"] = "Tepat Waktu"

    return hasil

@app.route("/absen-kamera")
def absen_kamera():
    return render_template("absen_kamera.html", active_page="daftar-absen")

@app.route("/laporan/edit-status-batch", methods=["POST"])
def edit_status_batch():
    tanggal = request.form.get("tanggal")

    for key in request.form:
        if key.startswith("status_"):
            karyawan_id = key.replace("status_", "")
            status = request.form.get(f"status_{karyawan_id}")
            keterangan = request.form.get(f"keterangan_{karyawan_id}", "")

            if status:
                set_status_manual(karyawan_id, tanggal, status, keterangan)

    return redirect(f"/laporan?tanggal={tanggal}")

@app.errorhandler(RequestEntityTooLarge)
def file_terlalu_besar(e):
    return jsonify({"error": "Ukuran file maksimal 5 MB"}), 413

if __name__ == "__main__":
    app.run(debug=True)