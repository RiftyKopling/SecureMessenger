
import cv2
import json
import numpy as np

from pathlib import Path


# ==================================
# PATH CONFIGURATION
# ==================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

FACES_DIR = PROJECT_DIR / "data" / "faces"
MODELS_DIR = PROJECT_DIR / "models"

MODEL_PATH = MODELS_DIR / "face_model.yml"
LABEL_PATH = MODELS_DIR / "face_labels.json"

SAMPLES_REQUIRED = 10
FACE_SIZE = (200, 200)


class FaceEnrollment:

    def __init__(self, display_name):

        self.display_name = display_name.strip()

        if len(self.display_name) < 3:
            raise ValueError("Display name minimal 3 karakter.")

        FACES_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        self.camera = None

        self.face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        if self.face_detector.empty():
            raise RuntimeError("Haar Cascade gagal dimuat.")

        self.samples = []

    # ==================================
    # OPEN CAMERA
    # ==================================

    def start_camera(self):

        if self.camera is not None:
            self.stop_camera()

        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None

            raise RuntimeError(
                "Kamera bawaan laptop tidak dapat dibuka."
            )

        return True

    # ==================================
    # STOP CAMERA
    # ==================================

    def stop_camera(self):

        if self.camera is not None:
            self.camera.release()
            self.camera = None

    # ==================================
    # READ CAMERA FRAME
    # ==================================

    def get_frame(self):

        if self.camera is None or not self.camera.isOpened():
            raise RuntimeError("Kamera belum aktif.")

        success, frame = self.camera.read()

        if not success:
            raise RuntimeError("Gagal membaca frame kamera.")

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )

        return frame, gray, faces

    # ==================================
    # CAPTURE FACE SAMPLE
    # ==================================

    def capture_sample(self, gray, face):

        if len(self.samples) >= SAMPLES_REQUIRED:
            raise RuntimeError(
                "Jumlah sampel wajah sudah mencapai batas."
            )

        x, y, w, h = face

        face_image = gray[y:y+h, x:x+w]

        face_image = cv2.resize(
            face_image,
            FACE_SIZE
        )

        face_image = cv2.equalizeHist(face_image)

        self.samples.append(face_image)

        return len(self.samples)

    # ==================================
    # TRAIN LBPH MODEL
    # ==================================

    def train_model(self):

        if len(self.samples) < SAMPLES_REQUIRED:
            raise RuntimeError(
                f"Dibutuhkan {SAMPLES_REQUIRED} sampel wajah. "
                f"Saat ini baru {len(self.samples)}."
            )

        labels = np.array(
            [1] * len(self.samples),
            dtype=np.int32
        )

        recognizer = cv2.face.LBPHFaceRecognizer_create()

        recognizer.train(
            self.samples,
            labels
        )

        recognizer.write(str(MODEL_PATH))

        LABEL_PATH.write_text(
            json.dumps(
                {
                    "1": self.display_name
                },
                indent=4
            ),
            encoding="utf-8"
        )

        return True



class FaceVerification:

    def __init__(self, threshold=70):
        if not MODEL_PATH.exists():
            raise FileNotFoundError("Face model belum tersedia.")

        if not LABEL_PATH.exists():
            raise FileNotFoundError("Face labels belum tersedia.")

        self.threshold = threshold

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(str(MODEL_PATH))

        self.labels = json.loads(
            LABEL_PATH.read_text(encoding="utf-8")
        )

        self.face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        if self.face_detector.empty():
            raise RuntimeError("Haar Cascade gagal dimuat.")

        self.camera = None

    def start_camera(self):
        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None
            raise RuntimeError("Kamera tidak dapat dibuka.")

    def stop_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def verify_frame(self, frame):

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )

        if len(faces) == 0:
            return {
                "recognized": False,
                "message": "No face detected."
            }

        if len(faces) > 1:
            return {
                "recognized": False,
                "message": "Multiple faces detected."
            }

        x, y, w, h = faces[0]

        face_image = gray[y:y+h, x:x+w]
        face_image = cv2.resize(face_image, FACE_SIZE)
        face_image = cv2.equalizeHist(face_image)

        label, distance = self.recognizer.predict(face_image)

        if distance <= self.threshold and str(label) in self.labels:
            return {
                "recognized": True,
                "name": self.labels[str(label)],
                "distance": float(distance)
            }

        return {
            "recognized": False,
            "message": "Unknown face.",
            "distance": float(distance)
        }

