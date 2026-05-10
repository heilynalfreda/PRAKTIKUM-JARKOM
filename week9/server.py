from socket import * 
import sys 

# Membuat server socket
serverSocket = socket(AF_INET, SOCK_STREAM) 

serverPort = 6789
serverSocket.bind(('', serverPort))
serverSocket.listen(1)

while True: 
    print('Ready to serve...') 

    connectionSocket, addr = serverSocket.accept()

    try: 
        # Menerima request
        message = connectionSocket.recv(1024).decode()
        filename = message.split()[1] 
        f = open(filename[1:]) 
        
        # Membaca isi file
        outputdata = f.read()

        # Mengirim HTTP Header
        connectionSocket.send("HTTP/1.1 200 OK\r\n".encode())
        connectionSocket.send("Content-Type: text/html\r\n".encode())
        connectionSocket.send("\r\n".encode()) 
  

        for i in range(0, len(outputdata)): 
            connectionSocket.send(outputdata[i].encode()) 
            
        connectionSocket.send("\r\n".encode()) 
        connectionSocket.close() 
        print(f"Berhasil mengirim {filename}")

    except IOError: 
        # Respon jika file tidak ditemukan (404)

        connectionSocket.send("HTTP/1.1 404 Not Found\r\n".encode())
        connectionSocket.send("Content-Type: text/html\r\n\r\n".encode())
        connectionSocket.send("<html><body><h1>404 File Tidak Ditemukan</h1></body></html>".encode())


        # Menutup socket client
        connectionSocket.close()


# Baris ini biasanya tidak tercapai karena loop 'while True'
serverSocket.close() 
sys.exit()