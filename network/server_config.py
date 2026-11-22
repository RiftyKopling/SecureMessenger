import json

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "config" / "server_config.json"


def load_server_config():

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Konfigurasi server tidak ditemukan."
        )

    try:

        config = json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )

        host = config["host"]
        port = int(config["port"])

        if not isinstance(host, str) or not host.strip():
            raise ValueError("Alamat server tidak valid.")

        if not 1 <= port <= 65535:
            raise ValueError("Port server tidak valid.")

        return host.strip(), port

    except (json.JSONDecodeError, KeyError, TypeError) as error:

        raise ValueError(
            f"Konfigurasi server tidak valid: {error}"
        )