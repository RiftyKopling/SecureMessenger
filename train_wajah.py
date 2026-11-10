# train_wajah.py
import cv2
import numpy as np
import os

DATASET_DIR = "dataset"

# Siapkan recognizer LBPH
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Siapkan detektor wajah (Haar Cascade bawaan OpenCV)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

wajah_list = []
label_list = []

# Loop semua folder user di dataset/
for label, nama_user in enumerate(os.listdir(DATASET_DIR)):
    folder = os.path.join(DATASET_DIR, nama_user)
    if not os.path.isdir(folder):
        continue

    print(f"Memproses user: {nama_user} (label={label})")

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        # Deteksi wajah di foto
        wajah = face_cascade.detectMultiScale(img, 1.1, 4)
        for (x, y, w, h) in wajah:
            roi = img[y:y+h, x:x+w]
            roi = cv2.resize(roi, (200, 200))  # samakan ukuran
            wajah_list.append(roi)
            label_list.append(label)

print(f"Total wajah diproses: {len(wajah_list)}")

# Latih model
recognizer.train(wajah_list, np.array(label_list))
recognizer.save("trainer.yml")

print("✅ Model disimpan ke trainer.yml")
