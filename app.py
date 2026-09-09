import os
import uuid
import json
from flask import Flask, request, jsonify, render_template, redirect
from datetime import time, timedelta, datetime, date as date_cls
from utils.face_utils import extract_embedding, embedding_to_binary, binary_to_embedding, compare_faces
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
    get_tren_7_hari
)

JAM_MASUK_STANDAR = time(8, 0)

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/daftar-absen")
def daftar_absen():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    tanggal = date_cls.today()
    summary = get_dashboard_summary(tanggal)
    tren = get_tren_7_hari(tanggal)

    labels = [item["tanggal"] for item in tren]
    values = [item["hadir"] for item in tren]

    return render_template(
        "dashboard.html",
        summary=summary,
        labels=json.dumps(labels),
        values=json.dumps(values)
    )

@app.route("/laporan")
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

    return render_template("laporan.html", data=data, tanggal=tanggal)

@app.route("/laporan/edit-status", methods=["POST"])
def edit_status_laporan():
    karyawan_id = request.form.get("karyawan_id")
    tanggal = request.form.get("tanggal")
    status = request.form.get("status")
    keterangan = request.form.get("keterangan")
    set_status_manual(karyawan_id, tanggal, status, keterangan)
    return redirect(f"/laporan?tanggal={tanggal}")

@app.route("/karyawan")
def karyawan():
    data = get_daftar_karyawan()
    return render_template("karyawan.html", data=data)

@app.route("/karyawan/edit/<int:karyawan_id>", methods=["GET", "POST"])
def edit_karyawan(karyawan_id):
    if request.method == "POST":
        nama = request.form.get("nama")
        nik = request.form.get("nik")
        file = request.files.get("foto")

        embedding_binary = None
        foto_path = None
        if file and file.filename != "":
            ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            embedding_baru = extract_embedding(filepath)
            if embedding_baru is None:
                return jsonify({"error": "Wajah tidak terdeteksi di foto baru"}), 400
            embedding_binary = embedding_to_binary(embedding_baru)
            foto_path = f"uploads/{unique_filename}"

        update_karyawan(karyawan_id, nama, nik, embedding_binary, foto_path)
        return redirect("/karyawan")

    row = get_karyawan_by_id(karyawan_id)
    if row is None:
        return jsonify({"error": "Karyawan tidak ditemukan"}), 404
    return render_template("edit_karyawan.html", karyawan=row)

@app.route("/karyawan/hapus/<int:karyawan_id>", methods=["POST"])
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
    if nik and cek_nik_sudah_ada(nik):
        return jsonify({"error": f"NIK '{nik}' sudah terdaftar untuk karyawan lain"}), 400

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)

    embedding = extract_embedding(filepath)
    if embedding is None:
        return jsonify({"error": "Wajah tidak terdeteksi di foto"}), 400

    wajah_mirip = cari_wajah_mirip(embedding)
    if wajah_mirip:
        karyawan_id, nama_terdaftar = wajah_mirip
        return jsonify({"error": f"Wajah ini sudah terdaftar sebagai '{nama_terdaftar}' (Id: {karyawan_id})"}), 400

    binary_data = embedding_to_binary(embedding)
    insert_karyawan(nama, binary_data, foto_path=f"uploads/{unique_filename}", nik=nik if nik else None)

    return jsonify({"message": f"Karyawan '{nama}' berhasil didaftarkan"}), 200

@app.route("/absen", methods=["POST"])
def absen():
    file = request.files.get("foto")
    if not file:
        return jsonify({"error": "Foto wajib diisi"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

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
            match_found = (karyawan_id, nama, distance)
            break

    if not match_found:
        return jsonify({"error": "Wajah tidak dikenali"}), 404

    karyawan_id, nama, distance = match_found
    absensi_row = get_absensi_hari_ini(karyawan_id)

    if absensi_row is None:
        insert_jam_masuk(karyawan_id)
        return jsonify({"message": f"{nama} berhasil absen masuk"}), 200
    elif absensi_row.JamKeluar is None:
        update_jam_keluar(absensi_row.Id)
        return jsonify({"message": f"{nama} berhasil absen keluar"}), 200
    else:
        return jsonify({"message": f"{nama} sudah absen masuk & keluar hari ini"}), 200

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

if __name__ == "__main__":
    app.run(debug=True)