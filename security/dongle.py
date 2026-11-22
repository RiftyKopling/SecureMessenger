
import ctypes
import hashlib
import json
import secrets

from pathlib import Path
from ctypes import wintypes

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config" / "device_config.json"
KEY_FILENAME = "dongle.key"

# WINDOWS API
if not hasattr(ctypes, "WinDLL"):
    raise RuntimeError(
        "USB Dongle module ini saat ini dibuat untuk Windows."
    )

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
DRIVE_REMOVABLE = 2


def get_drive_type(root):
    return kernel32.GetDriveTypeW(str(root))


def get_volume_serial(root):
    serial = wintypes.DWORD()
    result = kernel32.GetVolumeInformationW(
        str(root),
        None,
        0,
        ctypes.byref(serial),
        None,
        None,
        None,
        0
    )
    if not result:
        return None
    return f"{serial.value:08X}"


# DETECT USB DRIVES
def get_removable_drives():
    drives = []
    logical_drives = kernel32.GetLogicalDrives()
    for index in range(26):
        if not logical_drives & (1 << index):
            continue
        letter = chr(ord("A") + index)
        root = f"{letter}:\\"
        if get_drive_type(root) != DRIVE_REMOVABLE:
            continue
        serial = get_volume_serial(root)
        if serial is None:
            continue
        drives.append({
            "root": root,
            "serial": serial
        })
    return drives

# REGISTER USB DONGLE

def register_dongle(drive_root, display_name):
    drive_root = str(drive_root)
    display_name = str(display_name).strip()

    if len(display_name) < 3:
        raise ValueError("Display name minimal 3 karakter.")

    if not drive_root.endswith("\\"):
        drive_root += "\\"

    if get_drive_type(drive_root) != DRIVE_REMOVABLE:
        raise ValueError("Perangkat bukan removable drive.")

    serial = get_volume_serial(drive_root)

    if serial is None:
        raise RuntimeError("Tidak bisa membaca serial number USB.")

    key_path = Path(drive_root) / KEY_FILENAME

    if key_path.exists():
        raise FileExistsError("File dongle.key sudah ada pada USB.")

    if CONFIG_PATH.exists():
        raise FileExistsError(
            "Perangkat sudah pernah didaftarkan. "
            "Gunakan konfigurasi yang sudah ada."
        )

    secret_key = secrets.token_bytes(32)
    key_hash = hashlib.sha256(secret_key).hexdigest()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "version": 1,
        "display_name": display_name,
        "volume_serial": serial,
        "key_filename": KEY_FILENAME,
        "key_sha256": key_hash
    }

    try:
        key_path.write_bytes(secret_key)
        CONFIG_PATH.write_text(
            json.dumps(config, indent=4),
            encoding="utf-8"
        )
    except OSError:
        if key_path.exists():
            key_path.unlink()
        raise

    return True

# VERIFY USB DONGLE
def verify_dongle():

    if not CONFIG_PATH.exists():
        return {
            "valid": False,
            "message": "Dongle belum didaftarkan."
        }

    try:

        config = json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )

        expected_serial = config["volume_serial"]
        expected_hash = config["key_sha256"]
        key_filename = config["key_filename"]

    except (OSError, ValueError, KeyError, TypeError):

        return {
            "valid": False,
            "message": "Konfigurasi dongle tidak valid."
        }

    for drive in get_removable_drives():

        if drive["serial"] != expected_serial:
            continue

        key_path = Path(drive["root"]) / key_filename

        if not key_path.is_file():
            continue

        try:

            secret_key = key_path.read_bytes()

        except OSError:
            continue

        actual_hash = hashlib.sha256(
            secret_key
        ).hexdigest()

        if secrets.compare_digest(
            actual_hash,
            expected_hash
        ):

            return {
                "valid": True,
                "message": "USB Dongle berhasil diverifikasi.",
                "drive": drive["root"]
            }

    return {
        "valid": False,
        "message": "USB Dongle tidak ditemukan atau tidak valid."
    }

def reset_dongle(force=False):
    import hashlib
    import json
    from pathlib import Path

    if not CONFIG_PATH.exists():
        return {
            "valid": False,
            "message": "Tidak ada konfigurasi lama."
        }

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = json.load(file)

        old_serial = config.get("volume_serial")
        key_filename = config.get("key_filename")
        expected_hash = config.get("key_sha256")

        if not old_serial or not key_filename or not expected_hash:
            return {
                "valid": False,
                "message": "Konfigurasi lama tidak lengkap."
            }

        if Path(key_filename).name != key_filename:
            return {
                "valid": False,
                "message": "Nama file kunci tidak valid."
            }

        drives = get_removable_drives()

        old_drive = next(
            (
                drive for drive in drives
                if drive["serial"] == old_serial
            ),
            None
        )

        if old_drive is None:
            if not force:
                return {
                    "valid": False,
                    "message": (
                        "USB lama tidak ditemukan atau telah diformat. "
                        "Reset administratif diperlukan."
                    )
                }

            CONFIG_PATH.unlink()

            return {
                "valid": True,
                "message": (
                    "Konfigurasi lama berhasil dihapus. "
                    "Silakan daftarkan USB baru."
                )
            }

        key_path = Path(old_drive["root"]) / key_filename

        if not key_path.is_file():
            if not force:
                return {
                    "valid": False,
                    "message": "File kunci lama tidak ditemukan."
                }

            CONFIG_PATH.unlink()

            return {
                "valid": True,
                "message": "Konfigurasi lama berhasil dihapus."
            }

        actual_hash = hashlib.sha256(
            key_path.read_bytes()
        ).hexdigest()

        if actual_hash != expected_hash:
            return {
                "valid": False,
                "message": "Kunci USB tidak cocok. Reset dibatalkan."
            }

        key_path.unlink()
        CONFIG_PATH.unlink()

        return {
            "valid": True,
            "message": "Reset berhasil."
        }

    except (OSError, json.JSONDecodeError) as error:
        return {
            "valid": False,
            "message": f"Reset gagal: {error}"
        }

def update_display_name(display_name):
    display_name = str(display_name).strip()

    if len(display_name) < 3:
        raise ValueError("Display name minimal 3 karakter.")

    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Konfigurasi Dongle belum tersedia.")

    # Pastikan USB yang terdaftar masih valid.
    verification = verify_dongle()

    if not verification["valid"]:
        raise RuntimeError(
            "USB Dongle belum berhasil diverifikasi."
        )

    config = json.loads(
        CONFIG_PATH.read_text(encoding="utf-8")
    )

    config["display_name"] = display_name

    CONFIG_PATH.write_text(
        json.dumps(config, indent=4),
        encoding="utf-8"
    )

    return True


def get_dongle_secret():

    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "Konfigurasi USB Dongle belum tersedia."
        )

    try:

        config = json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )

        expected_serial = config["volume_serial"]
        expected_hash = config["key_sha256"]
        key_filename = config["key_filename"]

    except (OSError, ValueError, KeyError, TypeError):

        raise RuntimeError(
            "Konfigurasi USB Dongle tidak valid."
        )

    for drive in get_removable_drives():

        if drive["serial"] != expected_serial:
            continue

        key_path = Path(drive["root"]) / key_filename

        if not key_path.is_file():
            continue

        try:
            secret_key = key_path.read_bytes()
        except OSError:
            continue

        actual_hash = hashlib.sha256(
            secret_key
        ).hexdigest()

        if secrets.compare_digest(
            actual_hash,
            expected_hash
        ):

            if len(secret_key) != 32:
                raise RuntimeError(
                    "Panjang rahasia USB Dongle tidak valid."
                )

            return secret_key

    raise RuntimeError(
        "USB Dongle tidak ditemukan atau tidak valid."
    )
