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

def deteksi_kedipan(list_filepath, threshold_ear=0.21):
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

    if len(riwayat_ear) < 3:
        return False

    ear_minimum = min(riwayat_ear)
    ear_maksimum = max(riwayat_ear)

    return ear_minimum < threshold_ear and ear_maksimum > threshold_ear