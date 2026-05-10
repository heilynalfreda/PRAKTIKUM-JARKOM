from socket import *

serverPort = 8080 # port koneksi

#AF_INET = IP addr 4, SOCK_STREAM = TCP
serverSocket = socket(AF_INET, SOCK_STREAM)

# bind = menghubungkan socket dengan alamat dan port tertentu
# tuple = (x,y) = (alamat, port)
serverSocket.bind(('', serverPort))

# listen = menunggu koneksi dari client, 5 = jumlah koneksi yang bisa ditangani secara bersamaan
serverSocket.listen(5)
print("[SYSTEM] Server siap digunakan")

serverSocket.settimeout(1) # waktu timeout dalam detik
try:
    while True:
        try:    
            # accept = menerima koneksi dari client, mengembalikan socket baru untuk komunikasi dengan client dan alamat client
            connectionSocket, addr = serverSocket.accept()
            print("[SERVER] Koneksi diterima dari: ", addr)

            # menerima pesan dari client
            sentence = connectionSocket.recv(2048).decode() # mengubah bytes ke string, agar bisa dibaca manusia
            print("[SERVER] Pesan diterima: ", sentence)

            # mengubah pesan menjadi huruf kapital
            modifiedSentence = sentence.upper()
            print("[SERVER] Mengirim kembali pesan: ", modifiedSentence)

            # mengirim pesan kembali ke client
            connectionSocket.send(modifiedSentence.encode())

            # menutup koneksi dengan client
            connectionSocket.close()
        except timeout:
            continue #jika terjadi timeout, lanjutkan ke iterasi berikutnya untuk menerima koneksi baru
except KeyboardInterrupt:
    print("\n[SYSTEM] Server telah diberhentikan oleh pengguna.")
finally:
    # menutup socket server
    serverSocket.close()
    print("[SYSTEM] Socket telah ditutup. Program selesai.")