from socket import *

serverName = 'localhost'
serverPort = 8080 # port koneksi

#AF_INET = IP addr 4, SOCK_STREAM = TCP
clientSocket = socket(AF_INET, SOCK_STREAM)

#connect to server
clientSocket.connect((serverName, serverPort))

# send message to server
sentence = input('Input lowercase sentence: ')

clientSocket.send(sentence.encode())

# receive message from server
modifiedSentence = clientSocket.recv(2048) #menerima pesan dari server, 2048 = ukuran buffer
print('From Server: ', modifiedSentence.decode()) #decode = mengubah bytes ke string, agar bisa dibaca manusia

# close the socket
clientSocket.close()
print("[SYSTEM] Socket telah ditutup. Program selesai.")