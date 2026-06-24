"""
common.py — Modul utilitas bersama untuk Socket Programming
Hanya menggunakan Python Standard Library (tidak ada library eksternal)
"""

import socket # Digunakan untuk komunikasi jaringan TCP/IP
import json # Digunakan untuk serialisasi/deserialisasi header pesan dalam format JSON. serialisasi adalah proses mengubah objek Python menjadi format yang dapat dikirim melalui jaringan (dalam hal ini, string JSON), sedangkan deserialisasi adalah proses mengubah kembali string JSON menjadi objek Python.
import struct 
import os # Digunakan untuk operasi file dan path, seperti memeriksa ukuran file, membuat direktori, dan mengelola nama file.
from datetime import datetime

# ── Konstanta Jaringan ────────────────────────────────────────────────────────
SERVER_HOST = '0.0.0.0'    # Server: dengarkan semua interface (LAN + localhost)
CLIENT_HOST = '127.0.0.1'  # Client default — di-override via --host jika beda laptop
HOST        = CLIENT_HOST  # Alias untuk kompatibilitas (dipakai client.py)
PORT        = 12345
BUFFER_SIZE = 4096

# ── Tipe Pesan ────────────────────────────────────────────────────────────────
MSG_REGISTER      = 'register'
MSG_REGISTER_ACK  = 'register_ack' 
MSG_TEXT          = 'text'
MSG_FILE          = 'file'
MSG_CLIENT_LIST   = 'client_list'
MSG_ERROR         = 'error'
MSG_DISCONNECT    = 'disconnect'

# ── Ekstensi File yang Diizinkan ──────────────────────────────────────────────
EXT_DOCUMENT = {'.txt', '.docx', '.pdf'}
EXT_IMAGE    = {'.jpg', '.jpeg', '.png'}
EXT_AUDIO    = {'.mp3'}
EXT_VIDEO    = {'.mp4'}
ALL_EXTS     = EXT_DOCUMENT | EXT_IMAGE | EXT_AUDIO | EXT_VIDEO


# ═══════════════════════════════════════════════════════════════════════════════
#  Fungsi Protokol Utama
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk mengirim header JSON ke socket dengan prefiks panjang 4-byte (big-endian)
def send_header(sock: socket.socket, header: dict) -> None:
    """Kirim header JSON dengan prefiks 4-byte (big-endian) panjang header."""
    raw = json.dumps(header, ensure_ascii=False).encode('utf-8') # Konversi dict header ke JSON string, lalu encode ke bytes UTF-8. 
    sock.sendall(struct.pack('!I', len(raw)) + raw) # Kirim panjang header sebagai 4-byte big-endian diikuti oleh data header itu sendiri. Fungsi sendall memastikan bahwa seluruh data terkirim sebelum melanjutkan.

# Fungsi untuk menerima header JSON dari socket
def recv_header(sock: socket.socket):
    """
    Terima dan parse header JSON.
    Kembalikan dict jika berhasil, None jika koneksi terputus.
    """
    raw_len = _recv_exact(sock, 4)
    if raw_len is None:
        return None
    length = struct.unpack('!I', raw_len)[0]
    raw = _recv_exact(sock, length)
    if raw is None:
        return None
    return json.loads(raw.decode('utf-8'))

# Fungsi untuk mengirim payload file dari disk ke socket
def send_file_payload(sock: socket.socket, filepath: str,
                      label: str = 'Mengirim') -> None:
    """
    Stream file ke socket dalam chunk BUFFER_SIZE bytes.
    Menampilkan progress bar ASCII di terminal.
    """
    total = os.path.getsize(filepath)
    sent  = 0
    with open(filepath, 'rb') as f: 
        while True:
            chunk = f.read(BUFFER_SIZE) # Baca file dalam chunk sebesar BUFFER_SIZE (4096 bytes). Jika file lebih besar dari BUFFER_SIZE, proses ini akan diulang hingga seluruh file terkirim.
            if not chunk:
                break
            sock.sendall(chunk) # Kirim chunk ke socket. Fungsi sendall memastikan bahwa seluruh chunk terkirim sebelum melanjutkan.
            sent += len(chunk) # Update jumlah byte yang sudah terkirim.
            _print_progress(sent, total, label) # Tampilkan progress bar di terminal berdasarkan jumlah byte yang sudah terkirim dibandingkan dengan total ukuran file.
    if total > 0:
        print()   # newline setelah progress bar selesai


# Fungsi untuk menerima payload file dan menyimpannya ke disk 
def recv_file_payload(sock: socket.socket, save_path: str,
                      filesize: int, label: str = 'Menerima') -> None:
    """
    Terima tepat filesize byte dari socket dan simpan ke save_path.
    Menampilkan progress bar ASCII di terminal.
    """
    dirpath = os.path.dirname(save_path) 
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    received = 0
    with open(save_path, 'wb') as f:
        while received < filesize:
            to_read = min(BUFFER_SIZE, filesize - received)
            chunk   = sock.recv(to_read)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
            _print_progress(received, filesize, label)
    if filesize > 0:
        print()   # newline setelah progress bar selesai

# Fungsi untuk menerima payload file ke buffer bytes (digunakan untuk routing tanpa menyimpan ke disk)
def recv_bytes_buf(sock: socket.socket, n: int):
    """
    Terima tepat n byte ke dalam buffer bytes.
    Digunakan oleh server untuk mem-buffer payload file sebelum di-routing.
    Kembalikan bytes jika berhasil, None jika koneksi terputus.
    """
    return _recv_exact(sock, n)


# ═══════════════════════════════════════════════════════════════════════════════
#  Fungsi Helper
# ═══════════════════════════════════════════════════════════════════════════════

# Format ukuran file dalam bytes ke string yang mudah dibaca (B, KB, MB, GB).
def format_size(n: int) -> str:
    """Konversi bytes ke string yang mudah dibaca (B, KB, MB, GB)."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


# Buat path file unik dengan menambahkan timestamp jika file sudah ada.
def unique_filename(directory: str, filename: str) -> str:
    """
    Buat path file unik dengan menambahkan timestamp jika file sudah ada.
    Contoh: photo.jpg → photo_20260524_143022.jpg
    """
    base, ext = os.path.splitext(filename)
    ts         = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique     = f'{base}_{ts}{ext}'
    return os.path.join(directory, unique)

# Cetak garis pemisah dengan char tertentu (default '─').
def sep(char: str = '─', width: int = 55) -> None:
    """Cetak garis pemisah."""
    print(char * width)


# Cetak banner dengan judul di tengah, dikelilingi oleh char tertentu (default '═').
def banner(title: str, char: str = '═', width: int = 55) -> None:
    """Cetak banner dengan judul di tengah."""
    print(char * width)
    pad   = (width - len(title) - 2) // 2
    right = width - len(title) - pad - 2
    print(f"{char}{' ' * pad}{title}{' ' * right}{char}")
    print(char * width)


# ═══════════════════════════════════════════════════════════════════════════════
#  Internal
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi internal untuk menerima tepat n byte, digunakan oleh recv_header dan recv_file_payload
def _recv_exact(sock: socket.socket, n: int):
    """Terima tepat n byte. Return None jika koneksi terputus."""
    buf = b'' 
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf)) 
        except OSError:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


def _print_progress(current: int, total: int, prefix: str = '') -> None:
    """Progress bar ASCII tanpa library eksternal."""
    BAR    = 35
    filled = int(BAR * current / total) if total > 0 else BAR
    bar    = '█' * filled + '░' * (BAR - filled)
    pct    = 100.0 * current / total if total > 0 else 100.0
    print(
        # f'\r  {prefix}: [{bar}] {pct:5.1f}%  '
        f'\r  {pct:5.1f}%  '
        f'{format_size(current)}/{format_size(total)}',
        end='', flush=True
    )