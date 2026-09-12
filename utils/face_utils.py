import face_recognition
import numpy as np

def extract_embedding(image_path):
    # Baca gambar dan deteksi wajah
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        return None
    return encodings[0]

def embedding_to_binary(embedding):
    # Convert embedding (numpy array) jadi bytes
    return embedding.astype(np.float64).tobytes()

def binary_to_embedding(binary_data):
    # Convert bytes dari database balik jadi numpy array embedding
    return np.frombuffer(binary_data, dtype=np.float64)

def compare_faces(known_embedding, unknown_embedding, threshold=0.55):
    # Bandingkan dua embedding
    distance = np.linalg.norm(known_embedding - unknown_embedding)
    return distance <= threshold, distance

def hitung_ear(mata_points):
    mata_points = np.array(mata_points)
    A = np.linalg.norm(mata_points[1] - mata_points[5])
    B = np.linalg.norm(mata_points[2] - mata_points[4])
    C = np.linalg.norm(mata_points[0] - mata_points[3])
    ear = (A + B) / (2.0 * C)
    return ear

def deteksi_kedipan(list_filepath, threshold_ear=0.25):
    riwayat_ear = []

    for filepath in list_filepath:
        image = face_recognition.load_image_file(filepath)
        landmarks_list = face_recognition.face_landmarks(image)

        if len(landmarks_list) == 0:
            continue

        landmarks = landmarks_list[0]
        if 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            continue

        ear_kiri = hitung_ear(landmarks['left_eye'])
        ear_kanan = hitung_ear(landmarks['right_eye'])
        ear_rata = (ear_kiri + ear_kanan) / 2.0
        riwayat_ear.append(ear_rata)

    print(f"[DEBUG] Riwayat EAR: {riwayat_ear}")  # BARU — lihat nilai aslinya

    if len(riwayat_ear) < 3:
        print("[DEBUG] Frame tidak cukup untuk analisis EAR")  # BARU
        return False

    ear_minimum = min(riwayat_ear)
    ear_maksimum = max(riwayat_ear)
    print(f"[DEBUG] EAR min: {ear_minimum}, max: {ear_maksimum}")  # BARU

    return ear_minimum < threshold_ear and ear_maksimum > threshold_ear

def hitung_rasio_yaw(landmarks):
    """Rasio jarak hidung ke mata kiri vs kanan, untuk deteksi arah hadap wajah."""
    nose_x = sum(p[0] for p in landmarks['nose_tip']) / len(landmarks['nose_tip'])
    left_eye_x = min(p[0] for p in landmarks['left_eye'])
    right_eye_x = max(p[0] for p in landmarks['right_eye'])

    jarak_ke_kiri = abs(nose_x - left_eye_x)
    jarak_ke_kanan = abs(nose_x - right_eye_x)

    return jarak_ke_kiri / (jarak_ke_kanan + 1e-6)

def deteksi_menoleh(list_filepath, arah, ambang_perubahan=0.3):
    """
    Deteksi menoleh berdasarkan PERUBAHAN RELATIF dari rasio awal (baseline),
    bukan angka mutlak — lebih stabil untuk berbagai bentuk wajah/kondisi kamera.
    """
    riwayat_rasio = []

    for filepath in list_filepath:
        image = face_recognition.load_image_file(filepath)
        landmarks_list = face_recognition.face_landmarks(image)

        if len(landmarks_list) == 0:
            continue

        landmarks = landmarks_list[0]
        if 'nose_tip' not in landmarks or 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            continue

        riwayat_rasio.append(hitung_rasio_yaw(landmarks))

    print(f"[DEBUG] Arah: {arah}, Riwayat rasio: {riwayat_rasio}")

    if len(riwayat_rasio) < 3:
        return False

    baseline = riwayat_rasio[0]  # anggap frame pertama sebagai posisi awal
    perubahan_max = max(abs(r - baseline) / baseline for r in riwayat_rasio)

    print(f"[DEBUG] Baseline: {baseline}, Perubahan maksimum: {perubahan_max}")

    return perubahan_max > ambang_perubahan

def verifikasi_liveness(list_filepath, tantangan):
    if tantangan == "KEDIP":
        return deteksi_kedipan(list_filepath)
    elif tantangan in ("MENOLEH_KANAN", "MENOLEH_KIRI"):
        return deteksi_menoleh(list_filepath, tantangan)
    else:
        return False