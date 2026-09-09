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

def compare_faces(known_embedding, unknown_embedding, threshold=0.6):
    # Bandingkan dua embedding
    distance = np.linalg.norm(known_embedding - unknown_embedding)
    return distance <= threshold, distance