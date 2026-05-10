from socket import *

serverName = 'localhost'
serverPort = 3306, 80, 443

# ke kampus, kost, rumah =
serverName = 'localhost'
serverPort= 12000 # port koneksi

#AF_INET = IP addr 4, SOCK_DGRAM = UDP
clientSocket = socket(AF_INET, SOCK_DGRAM) 

# selama running = true, program akan berjalan terus
running = True
while running:
    message = input('> ') # input dari user, akan dikirim ke server
    if message.lower() == 'exit':
        print("[SYSTEM] Keluar dari program.")
        running = False
        continue
    else:
        # untuk mengirim pesan
        #encode = mengubah string ke bytes, karena socket hanya bisa kirim data bytes (mis: jarkom = 1010101001)
        clientSocket.sendto(message.encode(), (serverName, serverPort))
        
        # menerima pesan
        modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
        print("[SYSTEM] Pesan telah diterima dari: ", serverAddress)
        print(modifiedMessage.decode()) # decode = mengubah bytes ke string, agar bisa dibaca manusia

# setelah keluar dari loop, socket ditutup
clientSocket.close()
print("[SYSTEM] Socket telah ditutup. Program selesai.")