import cv2
import face_recognition
import requests
import time
import io

SERVER_URL = "http://127.0.0.1:5000/absen"
KAMERA_INDEX = 0  # ganti ke 1, 2, dst kalau kamera default salah

JUMLAH_FRAME_LIVENESS = 12
JEDA_ANTAR_FRAME = 0.15  # detik
DURASI_TAMPIL_HASIL = 3  # detik
COOLDOWN_SETELAH_HASIL = 2  # detik, jeda sebelum siap deteksi lagi

def frame_ke_bytes(frame):
    """Convert frame OpenCV (numpy array) jadi bytes JPEG untuk dikirim via HTTP."""
    ret, buffer = cv2.imencode('.jpg', frame)
    return io.BytesIO(buffer.tobytes())

def kirim_ke_server(frames):
    files = []
    for i, frame in enumerate(frames):
        buf = frame_ke_bytes(frame)
        files.append(('frames', (f'frame{i}.jpg', buf, 'image/jpeg')))

    try:
        response = requests.post(SERVER_URL, files=files, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": f"Gagal menghubungi server: {e}"}

def gambar_kotak_wajah(frame, lokasi_wajah):
    for (top, right, bottom, left) in lokasi_wajah:
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 200, 0), 2)

def gambar_overlay_hasil(frame, teks_utama, teks_sub, warna):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), warna, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame, teks_utama, (40, h // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, teks_sub, (40, h // 2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

def main():
    video = cv2.VideoCapture(KAMERA_INDEX)
    if not video.isOpened():
        print("Gagal membuka kamera. Cek KAMERA_INDEX atau koneksi webcam.")
        input("Tekan Enter untuk keluar...")
        return

    cv2.namedWindow("Absensi - PT Yuni Bersaudara Sejahtera", cv2.WINDOW_NORMAL)

    status = "IDLE"  # IDLE -> CAPTURING -> HASIL -> COOLDOWN
    waktu_status_berubah = time.time()
    hasil_terakhir = None

    while True:
        ret, frame = video.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # efek cermin, lebih natural buat user

        if status == "IDLE":
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            lokasi_wajah = face_recognition.face_locations(small_frame)
            lokasi_wajah_asli = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in lokasi_wajah]
            gambar_kotak_wajah(frame, lokasi_wajah_asli)

            cv2.putText(frame, "Arahkan wajah ke kamera...", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

            if len(lokasi_wajah) > 0:
                status = "CAPTURING"
                waktu_status_berubah = time.time()

        elif status == "CAPTURING":
            cv2.putText(frame, "Memverifikasi... jangan bergerak", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2, cv2.LINE_AA)
            cv2.imshow("Absensi - PT Yuni Bersaudara Sejahtera", frame)
            cv2.waitKey(1)

            frames_liveness = []
            for _ in range(JUMLAH_FRAME_LIVENESS):
                ret, f = video.read()
                if ret:
                    f = cv2.flip(f, 1)
                    frames_liveness.append(f)
                time.sleep(JEDA_ANTAR_FRAME)

            hasil_terakhir = kirim_ke_server(frames_liveness)
            status = "HASIL"
            waktu_status_berubah = time.time()

        elif status == "HASIL":
            if hasil_terakhir.get("message"):
                gambar_overlay_hasil(frame, hasil_terakhir["message"], "Terima kasih!", (30, 100, 30))
            else:
                gambar_overlay_hasil(frame, hasil_terakhir.get("error", "Gagal"), "Silakan coba lagi", (30, 30, 130))

            if time.time() - waktu_status_berubah > DURASI_TAMPIL_HASIL:
                status = "COOLDOWN"
                waktu_status_berubah = time.time()

        elif status == "COOLDOWN":
            cv2.putText(frame, "Bersiap untuk orang berikutnya...", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2, cv2.LINE_AA)
            if time.time() - waktu_status_berubah > COOLDOWN_SETELAH_HASIL:
                status = "IDLE"

        cv2.imshow("Absensi - PT Yuni Bersaudara Sejahtera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()