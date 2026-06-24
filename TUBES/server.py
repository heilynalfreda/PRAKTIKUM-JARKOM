"""
server.py — Server Socket Programming
Bertindak sebagai ROUTER / BRIDGE antar client (seperti WhatsApp server)

Mode:
  [1] Single Thread  — select() multiplexing, satu thread menangani semua client
  [2] Multi Thread   — threading.Thread per client, konkurensi penuh

Cara menjalankan:
  python server.py
"""

import socket
import threading
import select
import sys

# Local imports
from common import (
    HOST, SERVER_HOST, PORT, BUFFER_SIZE,
    MSG_REGISTER, MSG_REGISTER_ACK, MSG_TEXT, MSG_FILE,
    MSG_CLIENT_LIST, MSG_ERROR, MSG_DISCONNECT,
    send_header, recv_header, recv_bytes_buf,
    format_size, sep, banner,
)

# ── State Global ──────────────────────────────────────────────────────────────

clients      : dict[str, socket.socket] = {}   # username → socket 
clients_lock = threading.Lock() 


# ═══════════════════════════════════════════════════════════════════════════════
#  Routing 
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk meneruskan pesan dari satu client ke target yang sesuai
def route_message(header: dict, payload: bytes, sender_name: str) -> None:
    """
    Teruskan pesan (header + optional payload) ke target yang sesuai.
      header['target'] == 'ALL'  → broadcast ke semua kecuali pengirim
      ',' in header['target'] atau mode == 'multicast' → multicast ke beberapa client tertentu
      Selain itu                  → unicast ke satu client
    """
    target = header.get('target', 'ALL')
    mode = header.get('mode', 'unicast') 

    recipients = []
    mode_tag = 'UNICAST' 
    log_dest = target

    with clients_lock:
        # 1. CEK BROADCAST TERLEBIH DAHULU
        if target == 'ALL' or mode == 'broadcast':
            recipients = [(u, s) for u, s in clients.items() if u != sender_name]
            mode_tag = 'BROADCAST'
            log_dest = 'semua'
            
        # 2. CEK MULTICAST (Koma atau Mode bernilai multicast)
        elif ',' in target or mode == 'multicast':
            target_list = [t.strip() for t in target.split(',') if t.strip()] 
            for t in target_list:
                sock = clients.get(t) 
                if sock:
                    recipients.append((t, sock))
            mode_tag = 'MULTICAST'
            log_dest = f"[{', '.join([r[0] for r in recipients])}]" 
            
        # 3. JIKA BUKAN KEDUANYA, MAKA PASTI UNICAST
        else:
            sock = clients.get(target)
            if sock:
                recipients = [(target, sock)]
            mode_tag = 'UNICAST'
            log_dest = target

    # Jika target spesifik tidak ada yang online sama sekali (untuk Unicast / Multicast)
    if not recipients and target != 'ALL' and mode != 'broadcast':
        with clients_lock:
            sender_sock = clients.get(sender_name)
        if sender_sock:
            try:
                send_header(sender_sock, {
                    'type':     MSG_ERROR,
                    'message': f"Target pengiriman '{target}' tidak ditemukan atau sedang offline.",
                })
            except OSError:
                pass
        return

    # Log di terminal Server
    file_info = (f" [{header.get('filename', '')} | "
                 f"{format_size(header.get('filesize', 0))}]"
                 if header.get('type') == MSG_FILE else '') 
    print(f"  [{mode_tag}] {sender_name} → {log_dest}{file_info}")

    # Kirimkan data ke semua penerima yang valid di dalam list recipients
    for username, sock in recipients:
        try:
            send_header(sock, header) 
            if payload: 
                sock.sendall(payload) 
        except OSError as e:
            print(f"  [!] Gagal kirim ke {username}: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#  Registrasi & Disconnect Helper
# ═══════════════════════════════════════════════════════════════════════════════

# Fungsi untuk memproses registrasi client baru, digunakan di kedua mode
def _do_register(sock: socket.socket, addr, mode_tag: str):
    """
    Baca header registrasi pertama dari client baru.
    Daftarkan ke dict `clients`, kirim ACK, broadcast daftar client.
    Return username jika berhasil, None jika gagal.
    """
    
    header = recv_header(sock)
    if not header or header.get('type') != MSG_REGISTER:
        return None

    username = header.get('username', '').strip()
    if not username:
        return None

    with clients_lock:
        if username in clients:
            send_header(sock, {
                'type':    MSG_ERROR,
                'message': f"Nama '{username}' sudah digunakan. Pilih nama lain.",
            })
            return None
        clients[username] = sock # Daftarkan username dan socket ke dalam dict clients dengan kunci username dan nilai socket

    print(f"  [+] {username} terhubung dari {addr}  [{mode_tag}]")
    send_header(sock, {
        'type':    MSG_REGISTER_ACK,
        'message': f"Selamat datang, {username}! Anda kini terhubung.",
    })
    _broadcast_client_list()
    return username

# Fungsi untuk memproses disconnect client, digunakan di kedua mode
def _disconnect(sock: socket.socket, username: str) -> None:
    """Hapus client dari registry dan broadcast daftar client terbaru."""
    with clients_lock:
        clients.pop(username, None)
    print(f"  [-] {username} terputus")
    _broadcast_client_list()
    try:
        sock.close()
    except OSError:
        pass

# Fungsi untuk mengirim daftar client yang aktif ke semua client yang terkoneksi
def _broadcast_client_list() -> None:
    """Kirim daftar username yang aktif ke semua client yang terkoneksi."""
    with clients_lock:
        names = list(clients.keys())
        socks = list(clients.values())
    hdr = {'type': MSG_CLIENT_LIST, 'clients': names}
    for s in socks:
        try:
            send_header(s, hdr) 
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Mode 2 — Multi Thread
# ═══════════════════════════════════════════════════════════════════════════════

# Handler untuk satu client dalam mode Multi Thread
# conn adalah socket yang terhubung ke client, addr adalah alamat client (IP dan port)
def _handle_client_mt(conn: socket.socket, addr) -> None:
    """
    Handler satu client dalam mode Multi Thread.
    Setiap client berjalan di thread-nya sendiri → true concurrency.
    """
    username = _do_register(conn, addr, 'MT')
    if not username:
        conn.close()
        return

    try:
        while True:
            header = recv_header(conn)
            if not header:
                break  # koneksi terputus

            if header.get('type') == MSG_DISCONNECT:
                break

            # Terima payload file jika ada
            payload  = b'' 
            filesize = header.get('filesize', 0)
            if filesize > 0:
                print(f"  [MT] Menerima file dari {username} "
                      f"({format_size(filesize)}) — thread paralel")
                payload = recv_bytes_buf(conn, filesize)
                if payload is None:
                    break

            route_message(header, payload, username)

    except OSError:
        pass
    finally:
        _disconnect(conn, username)


# Fungsi untuk menjalankan server dalam mode Multi Thread
def run_multi_thread(server_sock: socket.socket) -> None:
    """
    Multi Thread mode:
    Setiap koneksi masuk mendapat thread baru (daemon).
    Semua thread berjalan paralel → tidak ada yang menunggu satu sama lain.
    """
    print("\n  ┌─ Multi Thread Mode ─────────────────────────────────")
    print("  │  Setiap client ditangani oleh thread terpisah")
    print("  │  Concurrent I/O — tidak ada client yang memblokir lainnya")
    print(f"  └─ Mendengarkan di 0.0.0.0:{PORT} (semua interface) ...\n")
    sep()

    while True:
        try:
            conn, addr = server_sock.accept()
            t = threading.Thread(
                target=_handle_client_mt,
                args=(conn, addr),
                daemon=True,
                name=f"client-{addr[1]}"
            )
            t.start()
        except OSError:
            break


# ═══════════════════════════════════════════════════════════════════════════════
#  Mode 1 — Single Thread (select-based)
# ═══════════════════════════════════════════════════════════════════════════════

# Handler untuk satu pesan dari client dalam mode Single Thread
def run_single_thread(server_sock: socket.socket) -> None:
    """
    Single Thread mode menggunakan select() untuk multiplexing I/O.
    Hanya ADA SATU THREAD — semua koneksi diproses secara bergantian.

    Keterbatasan yang diekspos:
    Saat menerima file besar dari satu client, pesan dari client lain
    harus menunggu di buffer OS hingga transfer selesai.
    """
    print("\n  ┌─ Single Thread Mode ────────────────────────────────")
    print("  │  Semua client ditangani dalam SATU thread via select()")
    print("  │  Saat file besar diterima, client lain menunggu")
    print(f"  └─ Mendengarkan di 0.0.0.0:{PORT} (semua interface) ...\n")
    sep() 

    
    sockets   = [server_sock] #  diambil dari socket server dan client yang terhubung
    usernames = {}   # sock → username (None = belum register)

    # Loop utama select() untuk menangani semua koneksi secara bergantian
    while True:
        try:
            readable, _, exceptional = select.select(
                sockets, [], sockets, 1.0
            ) 
        except OSError:
            break

        # Tangani socket yang punya data
        for s in readable:
            if s is server_sock:
                # Koneksi baru
                conn, addr = server_sock.accept()
                sockets.append(conn)
                usernames[conn] = None
                print(f"  [+] Koneksi baru dari {addr} (menunggu registrasi)")
            else:
                username = usernames.get(s)
                if username is None:
                    # Proses registrasi
                    name = _do_register_st(s, sockets, usernames)
                    if not name:
                        # Registrasi gagal, tutup koneksi
                        if s in sockets:
                            sockets.remove(s)
                        try:
                            s.close()
                        except OSError:
                            pass
                else:
                    # Proses pesan dari client terdaftar
                    ok = _handle_message_st(s, username)
                    if not ok:
                        if s in sockets:
                            sockets.remove(s)
                        usernames.pop(s, None)
                        _disconnect(s, username)

        # Tangani socket dengan error
        for s in exceptional:
            uname = usernames.pop(s, None)
            if s in sockets:
                sockets.remove(s)
            if uname:
                _disconnect(s, uname)
            else:
                try:
                    s.close()
                except OSError:
                    pass


# Proses registrasi dalam single-thread mode
def _do_register_st(sock: socket.socket, sockets: list, usernames: dict):
    """Proses registrasi dalam single-thread mode."""
    header = recv_header(sock)
    if not header or header.get('type') != MSG_REGISTER:
        return None

    username = header.get('username', '').strip()
    if not username:
        return None

    with clients_lock:
        if username in clients:
            send_header(sock, {
                'type':    MSG_ERROR,
                'message': f"Nama '{username}' sudah digunakan.",
            })
            return None
        clients[username] = sock

    usernames[sock] = username
    addr = sock.getpeername() 
    print(f"  [+] {username} terhubung dari {addr}  [ST]")
    send_header(sock, {
        'type':    MSG_REGISTER_ACK,
        'message': f"Selamat datang, {username}! Anda kini terhubung.",
    })
    _broadcast_client_list()
    return username


# Proses satu pesan dari client dalam single-thread mode
def _handle_message_st(sock: socket.socket, username: str) -> bool:
    """
    Baca dan proses SATU pesan dari client dalam single-thread mode.
    Return False jika client disconnect, True jika berhasil.

    PENTING: saat menerima file, fungsi ini MEMBLOK sampai seluruh
    payload diterima — inilah keterbatasan nyata single-thread!
    """
    header = recv_header(sock)
    if not header:
        return False

    if header.get('type') == MSG_DISCONNECT:
        return False

    payload  = b''
    filesize = header.get('filesize', 0)
    if filesize > 0:
        print(f"  [ST] ⚠ Menerima file dari {username} "
              f"({format_size(filesize)}) — semua client lain sedang menunggu!")
        payload = recv_bytes_buf(sock, filesize)
        if payload is None:
            return False

    route_message(header, payload, username)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Fungsi Main 
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None: 
    banner("SERVER SOCKET PROGRAMMING")
    print()
    print("  Pilih Mode Server:")
    print("  [1] Single Thread  — select() multiplexing, satu thread")
    print("  [2] Multi Thread   — threading.Thread per client")
    print()

    while True:
        choice = input("  >> Pilih mode [1/2]: ").strip()
        if choice in ('1', '2'):
            break
        print("  [!] Masukkan 1 atau 2.")

    # Inisialisasi server socket dan juga TCP socket untuk komunikasi yang handal
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    
    # Agar bisa langsung bind ulang ke port yang sama tanpa harus tunggu TIME_WAIT
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    
    try:
        server_sock.bind((SERVER_HOST, PORT))
    except OSError as e:
        print(f"\n  [!] Gagal bind ke {SERVER_HOST}:{PORT} — {e}")
        print(f"  [!] Pastikan port {PORT} tidak sedang digunakan.")
        sys.exit(1)
    server_sock.listen(20)

    # Tampilkan IP LAN agar client di laptop lain tahu harus konek ke mana
    try:
        lan_ip = socket.gethostbyname(socket.gethostname()) # berasal dari ip laptop sendiri
    except OSError:
        lan_ip = '(tidak terdeteksi)'
    print(f"\n  ── Info Koneksi ──────────────────────────────────────")
    print(f"  IP LAN laptop ini : {lan_ip}")
    print(f"  Port              : {PORT}")
    print(f"  Perintah client   : python client.py --host {lan_ip}")
    print(f"  ─────────────────────────────────────────────────────")
    print()

    # kondisi untuk memilih mode server, jika 1 maka jalankan single thread, jika 2 maka jalankan multi thread
    try:
        if choice == '1':
            run_single_thread(server_sock)
        else:
            run_multi_thread(server_sock)
    except KeyboardInterrupt:
        print("\n\n  [!] Server dihentikan oleh pengguna (Ctrl+C).")
    finally:
        server_sock.close()
        print("  Server ditutup.")


if __name__ == '__main__': 
    main()