# Meteor

HTML polos + Python (Flask). Tanpa CSS, database, atau proses build. Sedikit JavaScript di dalam HTML menangani Enter/Shift+Enter dan mencegah pengiriman ganda.

## Menjalankan

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
# Hanya jika .env belum ada:
Copy-Item .env.example .env
# Isi API_KEY_1 sampai API_KEY_6 di .env, lalu:
.\.venv\Scripts\python app.py
```

Buka http://127.0.0.1:8000. Jika `.env` sudah diisi, jangan ditimpa.
Key hanya dibaca backend dari `.env`; file ini diabaikan Git.

## Model dan perpindahan API

- OpenRouter menggunakan model percakapan tetap `google/gemma-4-31b-it:free`, dengan batas harga input/output/per-request nol. Pemilih acak `openrouter/free` tidak digunakan karena katalog gratis juga mencakup model moderasi yang menjawab dengan label seperti `User Safety: safe`. Tidak ada fallback ke model berbayar.
- Groq menggunakan `openai/gpt-oss-20b`. Penggunaannya gratis **hanya pada akun Free Plan**. Key Groq dilewati sampai `GROQ_FREE_PLAN_CONFIRMED=true` di `.env`. Aplikasi tidak dapat memverifikasi paket tagihan akun Groq melalui chat API.
- Key dicoba sesuai nomor. Key yang berhasil terus dipakai sampai gagal, lalu beralih ke key berikutnya. Maksimal satu percobaan per key untuk satu pesan.
- Jika respons menyebut model yang berbeda dari model yang diminta, respons ditolak dan aplikasi mencoba key berikutnya. Log hanya mencatat nomor API, penyedia, model yang diminta, dan status kegagalan; tidak mencatat key atau isi percakapan.
- Jika kuota habis, key tidak valid, jaringan bermasalah, atau layanan gagal, aplikasi mencoba key berikutnya. Key yang gagal diberi jeda sesuai `Retry-After`; jika tidak tersedia, 60 detik (1 jam untuk HTTP 401/402/403). Restart aplikasi setelah mengganti konfigurasi.
- Jika semuanya gagal, pesan tetap ada di form agar bisa dikirim ulang. Tidak ada pembelian kredit atau peningkatan paket otomatis.
- Beberapa key dalam akun/organisasi yang sama dapat berbagi kuota. Enam key tidak menjamin enam kali kuota; gratis juga bukan berarti tanpa batas.

## Percakapan

Riwayat dikirim bersama form HTML, terpisah pada setiap tab, tanpa disimpan di server atau database. Maksimal 10 pasang pesan dan 12.000 karakter dipertahankan; pasangan terlama dibuang ketika batas terlampaui. Satu pesan maksimal 4.000 karakter. Klik **Percakapan baru** untuk mengosongkan riwayat.

- **Enter** mengirim pesan; **Shift+Enter** membuat baris baru. Input IME tidak dikirim saat komposisi masih berlangsung.
- Klik **Edit** di pesan kamu, ubah isinya, lalu **Simpan dan kirim ulang**. Pesan itu dan jawabannya diganti; pesan setelahnya dihapus setelah jawaban baru berhasil. **Batal** mempertahankan percakapan. Jika API gagal, riwayat lama serta draf edit tetap tersedia untuk dicoba ulang.
- Tombol kirim dan edit tetap bekerja sebagai form HTML ketika JavaScript dimatikan; shortcut keyboard memerlukan JavaScript.

## Identitas Meteor

Identitas aplikasi dan asisten adalah **Meteor**. Instruksi identitas disisipkan backend pada setiap panggilan, termasuk setelah edit dan perpindahan API. Meteor tidak mengklaim model dasarnya dilatih sendiri.

Backend menyaring nama keluarga model dan penyedia yang digunakan sebelum jawaban ditampilkan atau dimasukkan ke riwayat. Penyaring memeriksa variasi kapitalisasi, spasi, tanda baca, Unicode, URL/HTML encoding, serta beberapa ejaan Base64, hex, ROT13, dan terbalik. Jawaban yang terdeteksi diganti dengan respons identitas Meteor; reasoning dan metadata model tidak ditampilkan. Pesan pengguna tidak disensor.

Ini pertahanan berlapis, bukan jaminan mutlak terhadap semua cara pengungkapan tersamar. Filter berfokus pada nama yang dikenal dan dapat turut memblokir pembahasan umum tentang nama tersebut. Jika model backend diganti, perbarui alias penyaring dan pengujiannya.

Backend berjalan pada komputer sendiri (`127.0.0.1`) dengan debug nonaktif. Balasan ditampilkan sebagai teks biasa, termasuk kode/Markdown.

## Pemeriksaan

Jalankan `.\.venv\Scripts\python -m unittest -v`. Pengujian memakai API tiruan, tanpa memakai kuota.

## Referensi

- [Gemma 4 31B versi gratis](https://openrouter.ai/google/gemma-4-31b-it:free)
- [Batas kuota OpenRouter](https://openrouter.ai/docs/api_reference/limits)
- [Model Groq](https://console.groq.com/docs/models)
- [Batas Free Plan Groq](https://console.groq.com/docs/rate-limits)
- [Tagihan Groq](https://console.groq.com/docs/billing-faqs)
