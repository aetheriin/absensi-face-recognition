from utils.face_utils import extract_embedding, embedding_to_binary, binary_to_embedding, compare_faces

emb1 = extract_embedding("test1.jpg")
emb2 = extract_embedding("test2.jpg")

if emb1 is None or emb2 is None:
    print("Wajah tidak terdeteksi di salah satu foto!")
else:
    # Tes convert ke binary dan balik lagi
    binary = embedding_to_binary(emb1)
    emb1_restored = binary_to_embedding(binary)

    match, distance = compare_faces(emb1_restored, emb2)
    print(f"Cocok: {match}, Jarak: {distance:.4f}")