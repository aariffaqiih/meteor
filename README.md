# Meteor

HTML + Python (Flask), tanpa database atau proses build. Tampilan bertema luar angkasa dengan warna hitam kebiruan dan cyan mengikuti `images/banner.png`; `images/profile_picture.png` menjadi avatar Meteor. CSS berada di HTML dengan nonce CSP, tanpa framework atau font eksternal. Sedikit JavaScript menangani Enter/Shift+Enter dan mencegah pengiriman ganda.

## Menjalankan

```cmd
# Pastikan dependencies terpasang (cukup sekali):
py -m pip install -r requirements.txt

# Hanya jika .env belum ada:
copy .env.example .env

# Isi API_KEY_1 sampai API_KEY_6 di .env, lalu jalankan:
py app.py
```

Buka http://127.0.0.1:8000. Jika `.env` sudah diisi, jangan ditimpa.
Key hanya dibaca backend dari environment atau `.env`; `.gitignore` mengecualikan `.env`. Jangan menaruh key di HTML.

## Hosting di GitHub Pages

Aplikasi ini sudah disiapkan agar bisa langsung di-hosting secara statis via GitHub Pages:
- `index.html` — frontend mandiri yang memanggil API langsung dari browser (dengan streaming & auto-fallback).
- `config.js` — memuat konfigurasi API key (OpenRouter / Groq).
- `.nojekyll` — memastikan GitHub Pages menyajikan semua file tanpa pemrosesan Jekyll.
- `images/` — aset visual (`banner.png` dan `profile_picture.png`).

### Cara Upload dan Mengaktifkan GitHub Pages:

> **Penting:** semua isi `config.js` dikirim ke browser dan dapat dilihat siapa pun.
> Jangan masukkan key pribadi, berbayar, atau yang masih ingin dirahasiakan. Jika
> ingin meneruskan percobaan dengan key publik, isi `CONFIG_API_KEYS` di file itu
> sebelum push. Key yang sebelumnya pernah tertulis di proyek sebaiknya segera
> dicabut/dirotasi di dashboard providernya.

1. **Commit dan Push ke Repository GitHub**:
```cmd
git add .
git commit -m "Deploy Meteor ke GitHub Pages"
git branch -M main
git remote add origin https://github.com/<username-kamu>/<nama-repo>.git
git push -u origin main
```
*(Ganti `<username-kamu>` dan `<nama-repo>` sesuai repository GitHub milikmu)*

2. **Aktifkan GitHub Pages di GitHub**:
- Buka repository di browser: `https://github.com/<username-kamu>/<nama-repo>`
- Klik menu **Settings** (tab atas)
- Pada sidebar kiri, klik **Pages**
- Pada bagian **Build and deployment**:
  - **Source**: pilih `GitHub Actions`
- Klik **Save**
- Tunggu sekitar 1–2 menit, GitHub Pages akan memberikan tautan aktif, misalnya:
  `https://<username-kamu>.github.io/<nama-repo>/`

Workflow `.github/workflows/deploy-pages.yml` akan berjalan setiap kali ada push
ke `main`, lalu hanya menerbitkan `index.html`, `config.js`, `.nojekyll`, dan
folder `images/`. Backend Flask dan file pengujian tidak ikut menjadi situs.

Cookie diperlukan untuk mengirim dan mengedit pesan. `METEOR_SECRET_KEY` boleh kosong: aplikasi membuat rahasia acak saat startup. Akibatnya form dari sebelum restart kedaluwarsa; muat ulang halaman. Untuk mempertahankan validitas form setelah restart, isi dengan rahasia acak pribadi seperti petunjuk `.env.example`. Konfigurasi yang tidak kosong tetapi kurang dari 32 byte UTF-8 ditolak saat startup; pemeriksaan panjang tidak dapat membuktikan keacakan rahasia.

## Model dan perpindahan API

- OpenRouter menggunakan model percakapan tetap `google/gemma-4-31b-it:free`, dengan batas harga input/output/per-request nol. Pemilih acak `openrouter/free` tidak digunakan karena katalog gratis juga mencakup model moderasi yang menjawab dengan label seperti `User Safety: safe`. Tidak ada fallback ke model berbayar.
- Groq menggunakan `openai/gpt-oss-20b`. Penggunaannya gratis **hanya pada akun Free Plan**. Key Groq dilewati sampai `GROQ_FREE_PLAN_CONFIRMED=true` di `.env`. Aplikasi tidak dapat memverifikasi paket tagihan akun Groq melalui chat API.
- Pada startup, key aktif dimulai dari nomor terkecil yang valid. Key kosong, duplikat, atau berformat tidak dikenal dilewati. Key yang berhasil terus dipakai sampai gagal, lalu beralih melingkar ke key berikutnya. Maksimal satu percobaan per key untuk satu pesan; key yang sedang menunggu jeda dilewati.
- Jika respons menyebut model yang berbeda dari model yang diminta, respons ditolak dan aplikasi mencoba key berikutnya. Log hanya mencatat nomor API, penyedia, model yang diminta, dan status kegagalan; tidak mencatat key atau isi percakapan.
- Jika kuota habis, key tidak valid, jaringan bermasalah, JSON rusak, atau respons tidak sesuai schema/batas, aplikasi mencoba key berikutnya selama anggaran waktu masih tersedia. `Retry-After` menerima detik atau HTTP date, dibatasi 1–86.400 detik. Header tidak valid/non-finite menggunakan 60 detik, atau 1 jam untuk HTTP 401/402/403. Jeda internal memakai jam monotonic. Restart aplikasi setelah mengganti konfigurasi.
- Timeout koneksi maksimal 5 detik dan timeout baca maksimal 20 detik, diperkecil sesuai sisa anggaran. Anggaran 45 detik menghentikan percobaan baru dan diperiksa saat menerima potongan respons. Ini **batas lunak**, bukan deadline total: DNS atau koneksi yang terus mengirim sedikit data dapat membuat waktu nyata lebih lama. Tidak semua enam key selalu dicoba. Lihat [semantik timeout Requests](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts).
- Koneksi HTTP dipakai ulang melalui satu `requests.Session`. Authorization diberikan per percobaan, cookie provider dibersihkan, redirect tidak diikuti, dan respons selalu ditutup. Body respons yang ditampung aplikasi dibatasi 128 KiB; jawaban teks dibatasi 8.000 karakter. Respons berlebih ditolak dan masuk alur fallback.
- Jika semuanya gagal, pesan tetap ada di form agar bisa dikirim ulang. Tidak ada pembelian kredit atau peningkatan paket otomatis.
- Beberapa key dalam akun/organisasi yang sama dapat berbagi kuota. Enam key tidak menjamin enam kali kuota; gratis juga bukan berarti tanpa batas.

## Percakapan

Riwayat dikirim bersama form HTML, terpisah pada setiap tab, tanpa penyimpanan percakapan di server atau database. Cookie berisi token sesi, bukan isi chat. Riwayat ditandatangani HMAC dan diikat ke sesi; perubahan isi hidden input riwayat tanpa tanda tangan yang sah ditolak. Tanda tangan bukan enkripsi: isi chat tetap ada di halaman browser dan dikirim ke provider untuk mendapatkan jawaban.

Maksimal 10 pasang pesan dan 12.000 karakter dipertahankan; pasangan terlama dibuang ketika jawaban baru membuat batas terlampaui. Satu pesan pengguna maksimal 4.000 karakter setelah whitespace tepi dibuang; jawaban maksimal 8.000. “Karakter” berarti Unicode code point: emoji gabungan dan huruf dengan combining mark dapat dihitung lebih dari satu. Lone surrogate ditolak. Klik **Percakapan baru** untuk mengosongkan riwayat.

- **Enter** mengirim pesan; **Shift+Enter** membuat baris baru. Input IME tidak dikirim saat komposisi masih berlangsung.
- Klik **Edit** di pesan kamu, ubah isinya, lalu **Simpan dan kirim ulang**. Pesan itu dan jawabannya diganti; pesan setelahnya dihapus setelah jawaban baru berhasil. **Batal** mempertahankan percakapan. Jika API gagal, riwayat lama serta draf edit tetap tersedia untuk dicoba ulang.
- Tombol kirim dan edit tetap bekerja sebagai form HTML ketika JavaScript dimatikan; shortcut keyboard memerlukan JavaScript.

## Identitas Meteor

Identitas aplikasi dan asisten adalah **Meteor**. Instruksi identitas disisipkan backend pada setiap panggilan, termasuk setelah edit dan perpindahan API. Meteor tidak mengklaim model dasarnya dilatih sendiri.

Backend menyaring nama keluarga model dan penyedia yang digunakan sebelum jawaban ditampilkan atau dimasukkan ke riwayat. Penyaring memeriksa variasi kapitalisasi, spasi, tanda baca, Unicode, URL/HTML encoding, serta beberapa ejaan Base64, hex, ROT13, dan terbalik. Jawaban yang terdeteksi diganti dengan respons identitas Meteor; reasoning dan metadata model tidak ditampilkan. Pesan pengguna tidak disensor.

Ini pertahanan berlapis, bukan jaminan mutlak terhadap semua cara pengungkapan tersamar. Filter berfokus pada nama yang dikenal dan dapat turut memblokir pembahasan umum tentang nama tersebut. Jika model backend diganti, perbarui alias penyaring dan pengujiannya.

Backend berjalan pada komputer sendiri (`127.0.0.1`) dengan debug nonaktif. Balasan ditampilkan sebagai teks biasa, termasuk kode/Markdown.

## Batas penggunaan lokal

Target aplikasi ini satu pengguna lokal, satu proses. Server menggunakan thread agar halaman tetap dapat dilayani ketika API menunggu; hanya satu panggilan chat dapat berjalan sekaligus. Pesan bersamaan mendapat HTTP 503 dengan petunjuk mencoba ulang. Maksimal 20 pengiriman valid per menit, dihitung bersama seluruh tab dalam satu proses, termasuk percobaan yang gagal. Batas ini mengembalikan HTTP 429 dan `Retry-After`; membuka percakapan baru tidak meresetnya. Edit/Batal tanpa regenerasi tidak memanggil API.

POST memerlukan token CSRF, sesi, dan tanda tangan riwayat. Origin lintas situs/rusak ditolak; hanya host localhost/loopback yang diterima. HTML tetap di-escape, CSP memakai nonce baru per respons, dan halaman memakai `no-store` serta `nosniff`. Cookie memakai HttpOnly dan SameSite=Strict. Body request maksimal 128 KiB dan form multipart maksimal 12 bagian. Form UTF-8 multipart menghindari pembengkakan URL encoding pada riwayat emoji.

Error yang diperkirakan memberi pesan lokal yang aman; error internal tak terduga menghasilkan HTTP 500 tanpa menampilkan exception mentah. Log aplikasi hanya mencatat metadata tetap atau nama kelas error. Launcher menonaktifkan access log Werkzeug yang dapat memuat query URL. Jika memakai server/proxy lain, aturan log server itu harus diperiksa tersendiri.

Ini belum konfigurasi layanan publik: tidak ada autentikasi pengguna, limiter lintas proses, atau TLS. Lock, cooldown, serta hitungan request hanya berlaku dalam satu proses dan direset ketika restart. Membuka akses internet memerlukan rancangan deployment tersendiri; jangan cukup mengganti host ke `0.0.0.0`. Secure cookie dan HSTS belum diaktifkan karena akses lokal menggunakan HTTP.

## Pemeriksaan

```cmd
py -m unittest -v
node test_frontend.cjs
py -m pip check
```

Test Python memakai provider tiruan dan satu server HTTP lokal untuk menguji pooling; tidak memakai kuota provider. Node hanya diperlukan untuk pemeriksaan JavaScript, bukan untuk menjalankan Meteor. Tidak ada dependency runtime tambahan.

Lihat [AUDIT.md](AUDIT.md) untuk klasifikasi temuan, test sebelum/sesudah, pengukuran, dan risiko tersisa. Pengukuran CPU dapat diulang dengan `python audit/profile_app.py`. Opsi `--network` mengakses endpoint metadata provider; `python audit/profile_chat.py --live` mengirim dua pesan sintetis dan memakai kuota gratis yang dikonfigurasi. Keduanya tidak mencetak key atau isi respons.

## Referensi

- [Gemma 4 31B versi gratis](https://openrouter.ai/google/gemma-4-31b-it:free)
- [Batas kuota OpenRouter](https://openrouter.ai/docs/api_reference/limits)
- [Model Groq](https://console.groq.com/docs/models)
- [Batas Free Plan Groq](https://console.groq.com/docs/rate-limits)
- [Tagihan Groq](https://console.groq.com/docs/billing-faqs)
