"""
client.py — Client Socket Programming
Setiap client bisa menjadi pengirim (A) maupun penerima (B) secara bersamaan
seperti WhatsApp / Discord.

Cara menjalankan:
  python client.py
  python client.py --host 192.168.x.x    ← jika server di mesin lain
"""

import socket
import threading
import os
import sys
import time

from common import (
    HOST, PORT, BUFFER_SIZE,
    MSG_REGISTER, MSG_REGISTER_ACK, MSG_TEXT, MSG_FILE,
    MSG_CLIENT_LIST, MSG_ERROR, MSG_DISCONNECT,
    EXT_DOCUMENT, EXT_IMAGE, EXT_AUDIO, EXT_VIDEO,
    send_header, recv_header,
    send_file_payload, recv_file_payload,
    unique_filename, format_size, sep, banner,
)

# ── Konfigurasi ───────────────────────────────────────────────────────────────
RECEIVED_DIR = 'received' # Direktori untuk menyimpan file yang diterima
os.makedirs(RECEIVED_DIR, exist_ok=True) 

# State global untuk menyimpan informasi koneksi, username, daftar client yang diketahui, dan sinkronisasi thread
# ── State Aplikasi ────────────────────────────────────────────────────────────
sock         : socket.socket = None
my_username  : str           = ''
known_clients: list          = []      # daftar username yang online (dari server)
stop_event                   = threading.Event()
print_lock                   = threading.Lock()
PROMPT                       = ''      # teks prompt, diisi setelah login


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper Print (thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi print thread-safe untuk menghindari output bercampur dengan prompt input.
def _safe_print(*args, **kwargs) -> None: 
    with print_lock:
        print(*args, **kwargs) #\


# Fungsi untuk mencetak ulang prompt setelah pesan masuk muncul di atas.
def _reprint_prompt() -> None:
    """Cetak ulang prompt setelah pesan masuk muncul di atas."""
    if PROMPT:
        print(f"  {PROMPT}", end='', flush=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Receiver Thread — background, selalu mendengarkan pesan dari server
# ═══════════════════════════════════════════════════════════════════════════════

# Receiver loop berjalan di thread terpisah, menerima semua pesan dari server,
def receiver_loop() -> None:
    """
    Berjalan di thread terpisah.
    Menerima semua pesan masuk dari server dan menampilkannya ke terminal.
    """
    # Perbarui daftar client yang diketahui saat menerima pesan dari server
    global known_clients 

    # Loop utama penerima — terus mendengarkan pesan dari server
    while not stop_event.is_set():
        try:
            header = recv_header(sock) 
            if header is None:
                _safe_print("\n  [!] Koneksi ke server terputus.")
                stop_event.set()
                break

            msg_type = header.get('type') 

            # ── Daftar client diperbarui ──────────────────────────────────────
            if msg_type == MSG_CLIENT_LIST: 
                known_clients = [c for c in header.get('clients', [])
                                 if c != my_username] 

            # ── Konfirmasi registrasi ─────────────────────────────────────────
            elif msg_type == MSG_REGISTER_ACK: 
                _safe_print(f"\n  ✓  {header.get('message', '')}")

            # ── Pesan teks masuk ──────────────────────────────────────────────
           # ── Pesan teks masuk ──────────────────────────────────────────────
            elif msg_type == MSG_TEXT:
                sender  = header.get('sender', '?')
                content = header.get('content', '') 
                mode    = header.get('mode', 'unicast')
                
                if mode == 'broadcast':
                    tag = '📢 BROADCAST'
                elif mode == 'multicast':
                    tag = '👥 MULTICAST'
                else:
                    tag = '💬 UNICAST'

                with print_lock:
                    print()
                    print(f"  ┌─ {tag} dari [{sender}] {'─'*25}")
                    # Tampilkan multi-baris dengan indent
                    for line in content.splitlines():
                        print(f"  │  {line}")
                    print(f"  └{'─'*45}")
                    _reprint_prompt() 

            # ── File masuk ────────────────────────────────────────────────────
            elif msg_type == MSG_FILE:
                sender   = header.get('sender', '?')
                filename = header.get('filename', 'file')
                filesize = header.get('filesize', 0)
                mode     = header.get('mode', 'unicast')
                ftype    = header.get('filetype', 'file')
                
                # Tentukan tag berdasarkan mode pengiriman
                if mode == 'broadcast':
                    tag = '📢 BROADCAST'
                elif mode == 'multicast':
                    tag = '📎 MULTICAST'
                else:
                    tag = '📎 UNICAST'
                    
                save_path = unique_filename(RECEIVED_DIR, filename) 

                with print_lock:
                    print()
                    print(f"  ┌─ {tag} File dari [{sender}] {'─'*20}")
                    print(f"  │  Nama    : {filename}")
                    print(f"  │  Ukuran  : {format_size(filesize)}")
                    print(f"  │  Tipe    : {ftype}")
                    print(f"  │  Simpan ke: {save_path}")
                    # Receive file — progress bar tampil di sini
                    recv_file_payload(sock, save_path, filesize)
                    print(f"  └─ ✓ File berhasil disimpan!")
                    _reprint_prompt()

            # ── Pesan error dari server ───────────────────────────────────────
            elif msg_type == MSG_ERROR:
                with print_lock:
                    print(f"\n  [!] Error: {header.get('message', '')}")
                    _reprint_prompt()

        except OSError:
            if not stop_event.is_set(): 
                _safe_print("\n  [!] Koneksi terputus mendadak.")
            stop_event.set()
            break


# ═══════════════════════════════════════════════════════════════════════════════
#  Fungsi Input Konten
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk mengirim payload file dari disk ke socket
def _input_words() -> str:
    """Input 1–5 kata, validasi jumlah kata."""
    while True:
        text  = input("  Ketik 1–5 kata: ").strip() 
        words = text.split()
        if 1 <= len(words) <= 5:
            return text
        print(f"  [!] Harus 1–5 kata (sekarang {len(words)} kata). Coba lagi.")

# Fungsi untuk menginput kalimat panjang (bisa multi-baris, akhiri dengan baris kosong).
def _input_sentence() -> str:
    """Input satu kalimat panjang."""
    while True:
        text = input("  Ketik kalimat panjang: ").strip()
        if text:
            return text
        print("  [!] Kalimat tidak boleh kosong.")


# Fungsi untuk menginput paragraf multi-baris (akhiri dengan baris kosong).
def _input_paragraph() -> str:
    """Input paragraf multi-baris (akhiri dengan baris kosong)."""
    print("  Ketik paragraf (akhiri dengan baris kosong):")
    lines = []
    while True:
        line = input("  > ")
        if line == '' and lines: 
            break
        if line:
            lines.append(line)
    return '\n'.join(lines) 


# Fungsi untuk menginput path file dengan validasi ekstensi dan keberadaan file.
def _input_file(allowed_exts: set, label: str) -> str:
    """Input dan validasi path file."""
    exts_str = ', '.join(sorted(allowed_exts)) # Buat string ekstensi yang diizinkan untuk ditampilkan di prompt
    while True:
        raw  = input(f"  Path file {label} ({exts_str}): ").strip().strip('"\'') 
        if not raw:
            return ''
        if not os.path.isfile(raw): 
            print(f"  [!] File tidak ditemukan: {raw}")
            continue
        ext = os.path.splitext(raw)[1].lower() # Ambil ekstensi file dan ubah ke huruf kecil untuk validasi
        if ext not in allowed_exts: # jika ekstensi tidak valid, tampilkan pesan error dan ulangi input
            print(f"  [!] Ekstensi tidak valid. Harus: {exts_str}")
            continue
        return raw


# ═══════════════════════════════════════════════════════════════════════════════
#  Fungsi Pengiriman
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk mengirim pesan teks ke target tertentu (unicast/multicast/broadcast).
def _send_text(content: str, target: str, mode: str) -> None:
    send_header(sock, {
        'type':    MSG_TEXT,
        'mode':    mode,
        'sender':  my_username,
        'target':  target,
        'content': content,
    })
    dest = 'semua client' if target == 'ALL' else target
    print(f"  ✓ Pesan terkirim ke {dest}.")


# Fungsi untuk mengirim file ke target tertentu (unicast/multicast/broadcast).
def _send_file(filepath: str, target: str, mode: str, filetype: str) -> None:
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    send_header(sock, {
        'type':     MSG_FILE,
        'mode':     mode,
        'sender':   my_username,
        'target':   target,
        'filename': filename,
        'filesize': filesize,
        'filetype': filetype,
    })
    print(f"  Mengirim {filename} ({format_size(filesize)}) ...")
    send_file_payload(sock, filepath)
    dest = 'semua client' if target == 'ALL' else target
    print(f"  ✓ File '{filename}' terkirim ke {dest}.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Sub-Menu Konten
# ═══════════════════════════════════════════════════════════════════════════════

_CONTENT_MENU = """\
  ┌─ Pilih Jenis Konten ───────────────────────────────
  │  [1] 1–5 Kata
  │  [2] Kalimat Panjang
  │  [3] Paragraf
  │  [4] File Dokumen  (.txt / .docx / .pdf)
  │  [5] Gambar        (.jpg / .jpeg / .png)
  │  [6] File Audio    (.mp3)
  │  [7] File Video    (.mp4)
  │  [0] Batal
  └────────────────────────────────────────────────────"""

# Fungsi untuk menampilkan menu konten dan memproses pilihan pengguna
def _content_menu(target: str, mode: str) -> None:
    """Tampilkan menu konten dan proses pilihan pengguna."""
    print(_CONTENT_MENU)
    choice = input("  >> Pilih [0-7]: ").strip()

    if choice == '0':
        return

    elif choice == '1':
        text = _input_words()
        _send_text(text, target, mode)

    elif choice == '2':
        text = _input_sentence()
        _send_text(text, target, mode)

    elif choice == '3':
        text = _input_paragraph()
        if text:
            _send_text(text, target, mode)
        else:
            print("  [!] Paragraf kosong, dibatalkan.")

    elif choice == '4':
        path = _input_file(EXT_DOCUMENT, 'Dokumen')
        if path:
            _send_file(path, target, mode, 'document')

    elif choice == '5':
        path = _input_file(EXT_IMAGE, 'Gambar')
        if path:
            _send_file(path, target, mode, 'image')

    elif choice == '6':
        path = _input_file(EXT_AUDIO, 'Audio')
        if path:
            _send_file(path, target, mode, 'audio')

    elif choice == '7':
        path = _input_file(EXT_VIDEO, 'Video')
        if path:
            _send_file(path, target, mode, 'video')

    else:
        print("  [!] Pilihan tidak valid.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Pemilihan Target Unicast
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk menampilkan daftar client online dan meminta pengguna memilih target unicast.
def _pick_target() -> str:
    """
    Tampilkan daftar client online dan minta pengguna memilih target.
    Kembalikan username target, atau '' jika batal/tidak ada.
    """
    online = list(known_clients)   # salinan agar tidak berubah saat iterasi

    if not online:
        print("  [!] Tidak ada client lain yang terhubung saat ini.")
        return ''

    print("\n  Client yang online:")
    for i, name in enumerate(online, 1):
        print(f"    [{i}] {name}")
    print("    [0] Batal")

    sel = input("  >> Pilih nomor: ").strip()
    if not sel.isdigit():
        print("  [!] Input tidak valid.")
        return ''
    idx = int(sel)
    if idx == 0:
        return ''
    if not (1 <= idx <= len(online)):
        print("  [!] Nomor di luar rentang.")
        return ''
    return online[idx - 1] 


# Fungsi untuk menampilkan daftar client online dan meminta pengguna memilih beberapa target multicast.
def _pick_multiple_targets() -> list:
    """
    Tampilkan daftar client online dan minta pengguna memilih beberapa target.
    Mengembalikan list username target, atau [] jika batal/tidak ada.
    """
    online = list(known_clients)

    if not online:
        print("  [!] Tidak ada client lain yang terhubung saat ini.")
        return []

    print("\n  Client yang online (Pilih beberapa, pisahkan dengan koma. Contoh: 1,3):")
    for i, name in enumerate(online, 1):
        print(f"    [{i}] {name}")
    print("    [0] Batal")

    sel = input("  >> Pilih nomor: ").strip()
    if sel == '0' or not sel:
        return []

    selected_targets = []
    # Memisahkan input berdasarkan koma
    parts = [p.strip() for p in sel.split(',')]
    
    for part in parts:
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(online):
                target_name = online[idx - 1]
                if target_name not in selected_targets:
                    selected_targets.append(target_name)
            else:
                print(f"  [!] Nomor {idx} di luar rentang, dilewati.")
        else:
            print(f"  [!] Input '{part}' tidak valid, dilewati.")

    return selected_targets

# ═══════════════════════════════════════════════════════════════════════════════
#  Main Sender Loop
# ═══════════════════════════════════════════════════════════════════════════════

_MAIN_MENU = """\
  ╔═══════════════════════════════════════════════════╗
  ║  [1]  Kirim Unicast   (A → satu client)           ║
  ║  [2]  Kirim Multicast (A → beberapa client)       ║
  ║  [3]  Kirim Broadcast (A → semua client)          ║
  ║  [4]  Lihat client yang sedang online             ║
  ║  [0]  Keluar                                      ║
  ╚═══════════════════════════════════════════════════╝"""

# Fungsi utama loop pengirim — menampilkan menu dan menangani input pengguna
def sender_loop() -> None:
    """
    Loop utama pengirim — berjalan di main thread.
    Menampilkan menu dan menangani input pengguna.
    """
    global PROMPT 

    while not stop_event.is_set():
        print(_MAIN_MENU)
        PROMPT = f"[{my_username}] >> "
        try:
            choice = input(f"  [{my_username}] >> ").strip() 
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            break

        if choice == '0':
            # Kirim notifikasi disconnect ke server
            try:
                send_header(sock, {
                    'type':   MSG_DISCONNECT,
                    'sender': my_username,
                })
            except OSError:
                pass 
            stop_event.set()
            break

        elif choice == '1':
            # ── UNICAST ──
            target = _pick_target()
            if target:
                print(f"\n  Target  : {target}")
                _content_menu(target, 'unicast') # Pastikan parameternya 'unicast'

        elif choice == '2':
            # ── MULTICAST ──
            targets = _pick_multiple_targets()
            if targets:
                # Menggabungkan nama target dengan koma sebagai penanda bagi server
                target_string = ','.join(targets)
                print(f"\n  Target-target: {', '.join(targets)}")
                _content_menu(target_string, 'multicast') # Pastikan parameternya 'multicast'

        elif choice == '3':
            # ── BROADCAST ──
            _content_menu('ALL', 'broadcast') # Pastikan parameternya 'broadcast'
            
        elif choice == '4':
            # Tampilkan daftar client yang sedang online
            online = list(known_clients)
            if not online:
                print("  [!] Tidak ada client lain yang terhubung saat ini.")
            else:
                print("\n  Daftar client yang sedang online:")
                for i, name in enumerate(online, 1):
                    print(f"    - {name}")
            print()
            
        else:
            print("  [!] Pilihan tidak valid. Silakan masukkan angka [0-4].\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi utama — mengatur koneksi, login, dan memulai thread penerima serta loop pengirim
def main() -> None:
    global sock, my_username, PROMPT

    # Baca argumen --host jika ada
    target_host = HOST
    for i, arg in enumerate(sys.argv[1:], 1): 
        if arg in ('--host', '-H') and i < len(sys.argv) - 1:
            target_host = sys.argv[i + 1]
            break
        elif arg.startswith('--host='):
            target_host = arg.split('=', 1)[1]
            break

    banner("CLIENT SOCKET PROGRAMMING")
    print()
    print(f"  Menghubungkan ke server {target_host}:{PORT} ...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Membuat socket TCP/IP. AF_INET menunjukkan bahwa kita menggunakan IPv4, dan SOCK_STREAM menunjukkan bahwa kita menggunakan protokol TCP.
    try:
        sock.connect((target_host, PORT))
    except ConnectionRefusedError:
        print(f"\n  [!] Gagal terhubung ke {target_host}:{PORT}")
        print("  [!] Pastikan server sudah berjalan terlebih dahulu.")
        sys.exit(1)
    except OSError as e:
        print(f"\n  [!] Error koneksi: {e}")
        sys.exit(1)

    print("  ✓ Terhubung ke server!\n")

    # Input username
    while True:
        username = input("  Masukkan nama pengguna Anda: ").strip()
        if username:
            break
        print("  [!] Nama tidak boleh kosong.")

    my_username = username
    PROMPT      = f"[{my_username}] >> "

    # Kirim registrasi
    send_header(sock, {
        'type':     MSG_REGISTER,
        'username': my_username,
    })

    # Tunggu respons registrasi
    ack = recv_header(sock)
    if not ack:
        print("  [!] Tidak ada respons dari server.")
        sys.exit(1)
    if ack.get('type') == MSG_ERROR:
        print(f"  [!] {ack.get('message', 'Registrasi gagal.')}")
        sys.exit(1)

    print(f"\n  ✓ {ack.get('message', 'Terdaftar!')}")
    print(f"  File yang diterima disimpan di: "
          f"{os.path.abspath(RECEIVED_DIR)}{os.sep}")
    sep()
    print()

    # Mulai receiver thread (background)
    t_recv = threading.Thread(
        target=receiver_loop,
        daemon=True,
        name="receiver"
    )
    t_recv.start()

    # Sender loop di main thread
    try:
        sender_loop()
    except KeyboardInterrupt:
        stop_event.set()

    # Cleanup
    try:
        sock.close()
    except OSError:
        pass
    print("\n  Sampai jumpa!")


if __name__ == '__main__':
    main()
