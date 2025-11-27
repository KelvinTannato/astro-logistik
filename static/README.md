Tentu! Berikut adalah penjelasan 100% lengkap mengenai seluruh fitur, logika, dan struktur dari proyek ASTRO SARANA INTERNASIONAL LOGISTIK versi final (Beta 0.7).

Proyek ini adalah sistem dashboard logistik incoming yang dibangun murni menggunakan HTML, CSS, dan Vanilla JavaScript, dengan fokus pada efisiensi workflow Admin dan pemisahan data pengguna/Admin.

🚀 Fitur dan Tujuan Utama
Sistem ini dirancang untuk memungkinkan Admin menginput data pengiriman (SMU) dan mempublikasikan update status serta estimasi waktu tiba (ETA) secara massal kepada Customer (pengguna biasa).

1. Struktur Data & Penyimpanan
Penyimpanan Lokal: Semua data (akun dan data SMU) disimpan di localStorage di browser pengguna. Ini menjadikannya solusi sederhana, cepat diakses, tetapi hanya berbasis client-side.

Pemisahan Data: Setiap data SMU memiliki properti createdBy (username penginput) dan publishedStatus/publishedEta (data yang resmi dilihat Customer).

2. Otentikasi dan Kontrol Akses
Akun: Akun disimpan dalam localStorage (astro_accounts). Akun default Admin: admin / admin.

Mode Admin: Admin dapat melihat semua data dari semua Customer.

Mode Pengguna: Pengguna biasa hanya dapat melihat data SMU yang mereka input (item.createdBy === currentUser).

Kontrol UI (CSS): Elemen sensitif (seperti tombol Hapus dan area Publikasi Update) disembunyikan menggunakan kelas admin-only yang diaktifkan/dinonaktifkan oleh JavaScript pada <body> (document.body.classList.toggle('admin-mode', isAdminMode)).

🌐 Penjelasan Per Bagian (HTML & CSS)
1. index.html (Struktur Halaman)
Layout: Menggunakan tata letak yang clean dengan card untuk memisahkan bagian (Input, Statistik, Tabel).

Form Input SMU: Disederhanakan. Hanya mencakup data dasar (Customer, SMU, Kota Asal, Koli, Transit, Tujuan). Data ETA/Status diisi kemudian oleh Admin.

Tabel Utama: Memiliki kolom untuk Status dan ETA, yang akan diisi dengan data published (untuk Customer) atau diisi dengan input field (untuk Admin—lihat JS).

Kontrol Admin: Area di atas tabel (#admin-update-controls) menampung dropdown Customer dan tombol "Publikasi Update".

2. style.css (Gaya dan UI/UX)
Tema: Dominan Biru (--primary-color) dan Putih/Abu Muda (--accent-color).

Estetika: Menggunakan font 'Poppins', soft shadow, dan border radius kecil (minimalis).

Badges Status: Menerapkan skema warna yang intuitif:

Merah (--status-red): Untuk status yang masih dalam perjalanan/transit (Masih di..., ... > ...).

Biru (--status-blue): Untuk status tiba di tujuan (Sampai di KNO).

Hijau (--status-green): Untuk status selesai (Sudah diterima).

In-Table Input Styling: Mengatur gaya input (<select>, <input type="text">) agar muat dan terlihat rapi di dalam sel tabel ketika Admin sedang melihat.

💻 Penjelasan Logika Inti (script.js)
1. Logika Update Status (Mass Direct Publish)
Ini adalah mekanisme unik di versi 0.7. Tombol Publikasi Update diaktifkan setelah Admin memilih Customer (#customer-select):

Pemilihan Customer: Fungsi populateCustomerSelect mengisi dropdown dengan nama-nama Customer unik dan opsi ALL_CUSTOMERS.

triggerStatusUpdateBtn (Direct Publish): Ketika diklik, fungsi ini tidak membuka modal, melainkan langsung memicu proses mass update:

Mengidentifikasi semua SMU milik selectedCustomerToUpdate.

Untuk setiap SMU, ia membaca nilai Status, ETA Bandara, dan ETA Door terbaru langsung dari elemen <select> dan <input type="text"> yang ada di baris tabel (DOM).

Menggunakan parseEtaInput untuk memvalidasi dan mengubah string HH.MM/DD menjadi format ISO standar.

Jika semua format valid, ia menimpa data published... di localStorage untuk SMU yang relevan.

Jika format ETA salah pada salah satu SMU, proses akan dibatalkan (thrown error), dan Admin menerima notifikasi.

2. Logika In-Table Editing (Render)
renderSmuTable(): Fungsi ini adalah inti pemisahan data:

Jika isAdminMode benar: Kolom Status, ETA Tiba, dan ETA Door dirender sebagai elemen form (<select>/<input type="text">) yang berisi nilai published terakhir. Admin dapat mengedit nilai ini.

Jika isAdminMode salah: Kolom tersebut dirender sebagai teks atau badge sederhana (<span class="status-badge">), menampilkan nilai yang dipublikasikan.

3. Logika Konversi Tanggal (ETA Parsing)
parseEtaInput(input): Mengambil input teks dalam format HH.MM/DD (misalnya, 16.00/12) dan mengkonversinya menjadi ISO String lengkap (YYYY-MM-DDT HH:MM:00), menggunakan bulan dan tahun saat ini sebagai default. Ini menyederhanakan entri data di lapangan.

formatTimeDisplay(isoString): Mengubah ISO String kembali menjadi format yang mudah dibaca (HH:MM (DD/MM)) untuk tampilan Customer.

4. Manajemen Data Internal
deleteSmu(id): Hanya dapat diakses oleh Admin, menghapus SMU dari localStorage.

updateStatistics(): Menghitung total SMU hari ini, SMU On Process (belum diterima), dan SMU Arrived (tiba/diterima), hanya menampilkan data yang relevan bagi pengguna yang sedang login.