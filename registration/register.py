
from security.dongle import (
    get_removable_drives,
    register_dongle
)


def main():

    print("=" * 40)
    print("     SECURE MESSENGER")
    print("       USB REGISTRATION")
    print("=" * 40)

    # 1. Mendeteksi USB
    print("\nMencari USB Dongle...")

    drives = get_removable_drives()

    if not drives:
        print("Tidak ada USB yang terdeteksi.")
        return

    # 2. Menampilkan USB yang ditemukan
    print("\nUSB yang tersedia:")

    for index, drive in enumerate(drives):

        print(
            f"{index + 1}. {drive['root']} "
            f"| Serial: {drive['serial']}"
        )

    # 3. Memilih USB
    try:

        choice = int(input("\nPilih USB: "))

        if choice < 1 or choice > len(drives):
            print("Pilihan tidak valid.")
            return

        selected_drive = drives[choice - 1]

        # 4. Konfirmasi
        confirmation = input(
            f"\nDaftarkan USB {selected_drive['root']}? (yes/no): "
        )

        if confirmation.lower() != "yes":
            print("Registrasi dibatalkan.")
            return

        # 5. Registrasi Dongle
        register_dongle(selected_drive["root"])

        print("\n" + "=" * 40)
        print("REGISTRASI BERHASIL!")
        print("USB Dongle berhasil didaftarkan.")
        print("=" * 40)

    except ValueError:
        print("Input tidak valid.")

    except (RuntimeError, OSError, FileExistsError) as error:
        print(f"Registrasi gagal: {error}")


if __name__ == "__main__":
    main()
