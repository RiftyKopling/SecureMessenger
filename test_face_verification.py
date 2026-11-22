
import cv2

from security.face_recognition import FaceVerification


def main():
    verifier = FaceVerification(threshold=70)

    try:
        verifier.start_camera()
        print("Kamera aktif.")
        print("Tekan Q untuk keluar.")

        while True:
            success, frame = verifier.camera.read()

            if not success:
                print("Gagal membaca kamera.")
                break

            result = verifier.verify_frame(frame)

            if result["recognized"]:
                name = result["name"]
                distance = result["distance"]

                text = f"Recognized: {name} ({distance:.2f})"
                color = (0, 255, 0)

            else:
                text = result["message"]

                if "distance" in result:
                    text += f" ({result['distance']:.2f})"

                color = (0, 0, 255)

            cv2.putText(
                frame,
                text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            cv2.imshow("Face Verification Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as error:
        print(f"Error: {error}")

    finally:
        verifier.stop_camera()
        cv2.destroyAllWindows()
        print("Kamera ditutup.")


if __name__ == "__main__":
    main()
