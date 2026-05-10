# Laporan Praktikum Modul 7: SOCKET PROGRAMMING: MEMBUAT APLIKASI JARINGAN

## Tujuan

1. Mampu membuat program berbasis socket UDP
2. Mampu membuat program berbasis socket TCP

## A. Program Socket dengan UDP

1. UDP Server

- UDP Server adalah untuk menyediakan titik akses yang selalu siap menerima paket data (datagram) dari banyak client sekaligus tanpa harus mengalokasikan sumber daya besar untuk memantau status setiap koneksi individu. Dengan bekerja secara stateless, server dapat memproses permintaan masuk dengan beban kerja (overhead) yang sangat rendah, menjadikannya solusi ideal untuk melayani ribuan perangkat secara bersamaan dalam aplikasi yang membutuhkan pembaruan data cepat seperti layanan DNS atau distribusi streaming media.
- udp-server.py

  ```python
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
  ```

2. UDP Client

- UDP Client adalah untuk memulai pengiriman data secara instan tanpa perlu melakukan proses sinkronisasi atau handshake yang memakan waktu, sehingga memungkinkan aplikasi untuk mengirimkan informasi dengan latensi sekecil mungkin. Client dalam model ini dirancang untuk skenario "kirim dan lupakan" (fire-and-forget), di mana fokus utamanya adalah kecepatan transmisi data ke alamat tujuan tanpa harus menunggu konfirmasi penerimaan atau menjaga koneksi tetap terbuka secara permanen.
- udp-client.py

  ```python
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
  ```

## B. Program Socket dengan TCP

1. TCP Server

- TCP Server adalah untuk menyediakan layanan yang stabil dengan mendengarkan permintaan koneksi masuk secara pasif dan mengelola sesi komunikasi yang berkelanjutan dengan setiap client secara individual. Server berfungsi untuk memvalidasi setiap paket data yang diterima, mengirimkan konfirmasi penerimaan (acknowledgment), dan mengatur aliran data agar tidak terjadi penumpukan (congestion control), sehingga integritas data tetap terjaga sepenuhnya dalam pertukaran informasi yang kompleks seperti transfer file atau layanan web.
- tcp-server.py

  ```python
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
  ```

2. TCP Client

- TCP Client adalah untuk menginisiasi permintaan koneksi secara aktif kepada server melalui proses three-way handshake guna memastikan bahwa jalur komunikasi telah siap sebelum data dikirimkan. Client bertanggung jawab untuk membangun sesi komunikasi yang aman, mengatur pengiriman ulang jika ada paket yang hilang di tengah jalan, serta memastikan bahwa data yang dikirimkan sampai ke tujuan dengan urutan yang benar dan tanpa kesalahan.
- tcp-client.py

  ```python
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
  ```

## Kesimpulan

Berdasarkan praktikum ini, dapat disimpulkan bahwa socket programming memungkinkan komunikasi antarperangkat melalui dua protokol utama dengan karakteristik berbeda: UDP yang bersifat connectionless dan stateless untuk transmisi data yang sangat cepat namun tanpa jaminan keutuhan, serta TCP yang bersifat connection-oriented untuk menjamin reliabilitas, urutan, dan integritas data melalui proses handshake dan konfirmasi pengiriman paket. Pemilihan antara keduanya sangat bergantung pada prioritas aplikasi, di mana UDP digunakan ketika latensi rendah menjadi kunci utama seperti pada streaming, sedangkan TCP digunakan ketika akurasi data tidak boleh dikompromikan seperti pada transfer dokumen atau layanan web.
