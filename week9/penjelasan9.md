# Laporan Praktikum Modul 9: WEB SERVER

## Tujuan

1. Mampu membuat program web server sederhana berbasis TCP socket
   programming.

## Implementasi Kode (Single-Threaded Web Server)

### Code Modul

```python
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
```

### Code HTML (hello.html)

```html
<!doctype html>
<html>
  <body>
    <h1>Hello, World!</h1>
    <p>Heilyn (103072400102).</p>
  </body>
</html>
```

### Penjelasan

Kode program di atas merupakan pembuatan web server mendasar yang bekerja melayani permintaan satu per satu secara bergantian (single-threaded). Alur dan mekanisme kerjanya adalah sebagai berikut:

1.  Inisialisasi Soket (socket): Server membuat sebuah pintu komunikasi (soket) baru berbasis IPv4 (AF_INET) dan menggunakan protokol TCP (SOCK_STREAM) yang menjamin pengiriman data secara aman dan utuh.
2.  Pengikatan Alamat dan Port (bind & listen): Melalui perintah bind, server menetapkan diri untuk beroperasi pada port 6789. Perintah listen(1) membuat server bersiap siaga memantau adanya koneksi masuk dari browser.
3.  Menerima Koneksi (accept): Memasuki perulangan while True, perintah serverSocket.accept() akan menahan jalannya program sampai ada browser yang mengakses alamat http://localhost:6789/hello.html. Begitu terhubung, server membuat soket baru bernama connectionSocket khusus untuk melayani klien tersebut.
4.  Membaca Permintaan (Parsing): Server menerima pesan HTTP Request dari browser, lalu memotong string teks tersebut (message.split()[1]) untuk mengambil nama file yang dicari (misal: /hello.html). Tanda garis miring (/) kemudian dibuang agar file lokal komputer dapat dibuka menggunakan fungsi open().
5.  Mengirim Respons Balasan:
    - Jika File Ditemukan (try): Server mengirimkan struktur HTTP Header sukses berupa HTTP/1.1 200 OK dan Content-Type: text/html yang dipisahkan baris kosong (\r\n). Setelah itu, isi dari dokumen HTML dikirimkan byte demi byte ke browser, lalu soket ditutup.
    - Jika File Tidak Ada (except IOError): Jika pengguna meminta file yang tidak ada di dalam folder, program akan otomatis dialihkan ke penanganan eror. Server akan merespons dengan kode standar internet HTTP/1.1 404 Not Found dan memunculkan tulisan teks pemberitahuan eror di layar browser pengguna.

## Tugas Tambahan: Multi-Threaded Web Server

### Code

```python
   from socket import *
   import sys
   import threading # Mengimpor modul threading untuk mendukung multi-thread

   # Fungsi khusus untuk menangani proses kirim-terima setiap client (proses di dalam thread)
   def handle_client(connectionSocket, addr):
      try:
         message = connectionSocket.recv(1024).decode()

         if not message or len(message.split()) < 2:
               connectionSocket.close()
               return

         filename = message.split()[1]
         filepath = filename[1:]

         if filepath.endswith(".html") or filepath.endswith(".htm"):
               content_type = "text/html"
               mode = "r" # Mode baca teks biasa
         elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
               content_type = "image/jpeg"
               mode = "rb" # Mode baca binary untuk gambar JPG
         elif filepath.endswith(".png"):
               content_type = "image/png"
               mode = "rb" # Mode baca binary untuk gambar PNG
         else:
               content_type = "application/octet-stream"
               mode = "rb"

         # Membaca isi file sesuai modenya
         with open(filepath, mode) as f:
               outputdata = f.read()

         # Mengirim HTTP Header dengan Content-Type yang dinamis
         connectionSocket.send("HTTP/1.1 200 OK\r\n".encode())
         connectionSocket.send(f"Content-Type: {content_type}\r\n".encode())
         connectionSocket.send("\r\n".encode())

         if mode == "rb":
               connectionSocket.sendall(outputdata)
         else:
               connectionSocket.sendall(outputdata.encode())

         connectionSocket.send("\r\n".encode())
         connectionSocket.close()
         print(f"Berhasil mengirim {filename} ke {addr}")

      except IOError:
         # Respon jika file tidak ditemukan (404)
         connectionSocket.send("HTTP/1.1 404 Not Found\r\n".encode())
         connectionSocket.send("Content-Type: text/html\r\n\r\n".encode())
         connectionSocket.send("<html><body><h1>404 File Tidak Ditemukan</h1></body></html>".encode())

         connectionSocket.close()

   serverSocket = socket(AF_INET, SOCK_STREAM)
   serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

   serverPort = 6789
   serverSocket.bind(('', serverPort))
   serverSocket.listen(5)

   while True:
      print('Ready to serve...')

      connectionSocket, addr = serverSocket.accept()

      client_thread = threading.Thread(target=handle_client, args=(connectionSocket, addr))
      client_thread.start()

   # Baris ini biasanya tidak tercapai karena loop 'while True'
   serverSocket.close()
   sys.exit()
```

### Code HTML (hello.html)

```html
<!doctype html>
<html>
  <body>
    <h1>Hello, World!</h1>
    <p>Heilyn (103072400102).</p>
    <img src="Aboutyou.jpg" alt="Foto Praktikum" width="300" />
  </body>
</html>
```

### Penjelasan

Pada tugas tambahan, web server dikembangkan agar mampu menangani beberapa permintaan browser secara bersamaan (paralel) tanpa adanya antrean yang membeku (blocking), sekaligus mampu membaca objek gambar. Perubahan mendasar yang terjadi meliputi:

1. Penggunaan Modul threading: Pada server single-threaded, jika ada satu proses kirim file yang lambat, klien lain harus menunggu antrean. Di kode ini, setiap ada koneksi masuk pada serverSocket.accept(), server langsung membuat thread (anak proses) baru melalui perintah threading.Thread(target=handle_client, ...). Tugas melayani klien langsung dilempar ke fungsi handle_client di latar belakang (background), sehingga perulangan utama while True milik server bisa langsung kembali bersiap menerima koneksi baru berikutnya tanpa tertahan.
2. Pengecekan Tipe Konten Secara Dinamis: Di dalam fungsi handle_client, terdapat seleksi kondisi if-elif. Jika file yang diminta berakhiran .html, server mengatur jenis konten berupa text/html dengan mode baca teks biasa (r). Namun, jika yang diminta adalah gambar berformat .jpg atau .png, server mengubah jenis konten menjadi image/jpeg atau image/png dan membuka file menggunakan mode binary (rb). Hal ini sangat krusial agar browser tahu cara membaca file tersebut sebagai gambar, bukan teks acak.
3. Pengiriman Data Optimal (sendall): Proses perulangan karakter pada modul utama diganti menggunakan fungsi .sendall(). Fungsi ini menjamin seluruh potongan data gambar yang berukuran relatif besar akan dikirimkan secara utuh ke jaringan tanpa ada byte yang terputus atau rusak di tengah jalan.
4. Optimasi Soket (SO_REUSEADDR): Ditambahkan fungsi perintah setsockopt untuk mengizinkan penggunaan kembali nomor port 6789 secara langsung sesaat setelah server dimatikan, tanpa harus menunggu waktu penundaan (time-wait) dari sistem operasi komputer.

## Kesimpulan

Berdasarkan hasil percobaan dan analisis pada praktikum Modul 9 ini, dapat disimpulkan bahwa protokol HTTP pada layer aplikasi bekerja secara sinkron di atas protokol transport TCP yang andal (reliable), di mana komunikasi yang diawali oleh request dari browser akan diselesaikan melalui pemberian paket data response header dan body dari sisi server. Meskipun pembuatan web server berbasis single-threaded sudah dapat berfungsi, model ini sangat tidak efisien untuk melayani banyak pengguna karena sifatnya yang blocking, sehingga proses pengunduhan data besar oleh satu pengguna akan menahan hak akses pengguna lainnya. Sebagai solusinya, pengembangan web server menjadi multi-threaded menggunakan bahasa Python berhasil memecahkan masalah antrean tersebut (concurrency) dengan cara mendelegasikan setiap koneksi masuk ke dalam jalur thread independen yang terpisah, sehingga pengiriman halaman web hello.html dan objek gambar Aboutyou.jpg dapat diproses secara bersamaan, cepat, dan mulus.
