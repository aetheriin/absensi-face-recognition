import pyodbc
from config import get_connection_string
from datetime import date, datetime, timedelta

def get_connection():
    conn_str = get_connection_string()
    return pyodbc.connect(conn_str)

def test_connection():
    try:
        conn = get_connection()
        print("Koneksi ke SQL Server berhasil!")
        conn.close()
        return True
    except Exception as e:
        print("Gagal konek ke SQL Server:", e)
        return False

def get_dashboard_summary(tanggal):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Karyawan")
    total_karyawan = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Absensi WHERE Tanggal = ? AND JamMasuk IS NOT NULL", tanggal)
    hadir = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Absensi WHERE Tanggal = ? AND JamMasuk > '08:00:00'", tanggal)
    telat = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Absensi WHERE Tanggal = ? AND Status IN ('Izin', 'Sakit', 'Cuti')", tanggal)
    izin_dll = cursor.fetchone()[0]

    conn.close()
    return {
        "total_karyawan": total_karyawan,
        "hadir": hadir,
        "telat": telat,
        "izin_dll": izin_dll
    }

def get_tren_7_hari(tanggal_akhir):
    tanggal_awal = tanggal_akhir - timedelta(days=6)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Tanggal, COUNT(*) as Hadir
        FROM Absensi
        WHERE JamMasuk IS NOT NULL AND Tanggal BETWEEN ? AND ?
        GROUP BY Tanggal
    """, tanggal_awal, tanggal_akhir)
    rows = {row.Tanggal: row.Hadir for row in cursor.fetchall()}
    conn.close()

    hasil = []
    for i in range(7):
        tgl = tanggal_awal + timedelta(days=i)
        hasil.append({"tanggal": tgl.strftime("%d %b"), "hadir": rows.get(tgl, 0)})
    return hasil

def insert_karyawan(nama, embedding_binary, foto_path=None, nik=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Karyawan (Nama, NIK, FaceEmbedding, FotoPath) VALUES (?, ?, ?, ?)",
        nama, nik, embedding_binary, foto_path
    )
    conn.commit()
    conn.close()

def get_all_karyawan():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Nama, FaceEmbedding FROM Karyawan")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_daftar_karyawan():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, NIK, Nama, FotoPath, CreatedAt FROM Karyawan ORDER BY CreatedAt ASC")
    columns = [column[0] for column in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return data

def get_karyawan_by_id(karyawan_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, NIK, Nama, FotoPath FROM Karyawan WHERE Id = ?", karyawan_id)
    row = cursor.fetchone()
    conn.close()
    return row

def update_karyawan(karyawan_id, nama, nik=None, embedding_binary=None, foto_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    if embedding_binary is not None:
        cursor.execute(
            "UPDATE Karyawan SET Nama = ?, NIK = ?, FaceEmbedding = ?, FotoPath = ? WHERE Id = ?",
            nama, nik, embedding_binary, foto_path, karyawan_id
        )
    else:
        cursor.execute(
            "UPDATE Karyawan SET Nama = ?, NIK = ? WHERE Id = ?",
            nama, nik, karyawan_id
        )
    conn.commit()
    conn.close()

def delete_karyawan(karyawan_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Absensi WHERE KaryawanId = ?", karyawan_id)
    cursor.execute("DELETE FROM Karyawan WHERE Id = ?", karyawan_id)
    conn.commit()
    conn.close()

def get_absensi_hari_ini(karyawan_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT Id, JamMasuk, JamKeluar FROM Absensi WHERE KaryawanId = ? AND Tanggal = ?",
        karyawan_id, date.today()
    )
    row = cursor.fetchone()
    conn.close()
    return row

def insert_jam_masuk(karyawan_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Absensi (KaryawanId, Tanggal, JamMasuk) VALUES (?, ?, ?)",
        karyawan_id, date.today(), datetime.now().time()
    )
    conn.commit()
    conn.close()

def update_jam_keluar(absensi_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Absensi SET JamKeluar = ? WHERE Id = ?",
        datetime.now().time(), absensi_id
    )
    conn.commit()
    conn.close()

def get_laporan_by_tanggal(tanggal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT k.Id AS KaryawanId, k.Nama, a.JamMasuk, a.JamKeluar, a.Status, a.Keterangan
        FROM Karyawan k
        LEFT JOIN Absensi a ON a.KaryawanId = k.Id AND a.Tanggal = ?
        ORDER BY k.Nama
    """, tanggal)
    columns = [column[0] for column in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return data

def set_status_manual(karyawan_id, tanggal, status, keterangan):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id FROM Absensi WHERE KaryawanId = ? AND Tanggal = ?", karyawan_id, tanggal)
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE Absensi SET Status = ?, Keterangan = ? WHERE Id = ?", status, keterangan, row.Id)
    else:
        cursor.execute(
            "INSERT INTO Absensi (KaryawanId, Tanggal, Status, Keterangan) VALUES (?, ?, ?, ?)",
            karyawan_id, tanggal, status, keterangan
        )
    conn.commit()
    conn.close()

def cek_nik_sudah_ada(nik, exclude_id=None):
    if not nik:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    if exclude_id:
        cursor.execute("SELECT Id FROM Karyawan WHERE NIK = ? AND Id != ?", nik, exclude_id)
    else:
        cursor.execute("SELECT Id FROM Karyawan WHERE NIK = ?", nik)
    row = cursor.fetchone()
    conn.close()
    return row is not None

def cari_wajah_mirip(embedding_baru, threshold=0.55, exclude_id=None):
    # Pengecekan karyawan yang sudah terdaftar
    from utils.face_utils import binary_to_embedding, compare_faces

    karyawan_list = get_all_karyawan()
    for row in karyawan_list:
        karyawan_id, nama, embedding_binary = row
        if exclude_id and karyawan_id == exclude_id:
            continue
        embedding_tersimpan = binary_to_embedding(embedding_binary)
        is_match, distance = compare_faces(embedding_tersimpan, embedding_baru, threshold)
        if is_match:
            return (karyawan_id, nama)
    return None

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Username, PasswordHash, NamaLengkap, Role FROM Users WHERE Username = ?", username)
    row = cursor.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Username, NamaLengkap, Role FROM Users WHERE Id = ?", user_id)
    row = cursor.fetchone()
    conn.close()
    return row

def update_last_login(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET LastLogin = GETDATE() WHERE Id = ?", user_id)
    conn.commit()
    conn.close()

def insert_user(username, password_hash, nama_lengkap, role="hrd"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Users (Username, PasswordHash, NamaLengkap, Role) VALUES (?, ?, ?, ?)",
        username, password_hash, nama_lengkap, role
    )
    conn.commit()
    conn.close()