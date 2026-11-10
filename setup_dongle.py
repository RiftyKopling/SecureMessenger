# setup_dongle.py
import subprocess
import json

# ====== GANTI HURUF DRIVE FLASHDISK KAMU ======
DRIVE = "E:"

# 1. Ambil serial number flashdisk
def get_serial(drive):
    output = subprocess.check_output(f"vol {drive}", shell=True, text=True)
    for line in output.splitlines():
        if "Serial Number" in line:
            return line.split()[-1]
    return None

# 2. Ambil serial
serial = get_serial(DRIVE)
print("Serial flashdisk:", serial)

# 3. Buat file kunci sederhana di flashdisk
with open(f"{DRIVE}/dongle.key", "w") as f:
    f.write("INI_DONGLE_RAHASIA_123")

# 4. Simpan serial ke file config di komputer
with open("config.json", "w") as f:
    json.dump({"serial": serial}, f)

print("✅ Dongle berhasil didaftarkan!")
print("File dongle.key dibuat di flashdisk.")