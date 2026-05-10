from socket import *

serverPort = 12000 # port koneksi
#AF_INET = IP addr 4, SOCK_DGRAM = UDP
serverSocket = socket(AF_INET, SOCK_DGRAM)

# bind = menghubungkan socket dengan alamat dan port tertentu
# tuple = (x,y) = (alamat, port) 
serverSocket.bind(('', serverPort))

print("[SYSTEM] Server siap digunakan")

#dijalankan terus selama program belum dihentikan
running = True
while running:
    # menerima pesan dari client
    message, clientAddress = serverSocket.recvfrom(2048)
    print("[SERVER] Pesan telah diterima dari: ", clientAddress)
    # message yg diterima = 101010100101

    decodeMessage = message.decode() # mengubah bytes ke string, agar bisa dibaca manusia
    # jika pesan = "exit"
    if decodeMessage.lower() == 'exit':
        print("[SYSTEM] Server telah diberhentikan.")
        running = False
        continue
    
    # mengubah pesan menjadi huruf kapital
    modifiedMessage = decodeMessage.upper()
    print("[SERVER] diterima dari ", clientAddress, " message: ", decodeMessage)

    # mengirim pesan kembali ke client
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)

# setelah keluar dari loop, socket ditutup
serverSocket.close()    
print("[SYSTEM] Socket telah ditutup. Program selesai.")



