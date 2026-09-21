# Audit dan pengerasan Meteor

Catatan perubahan berikutnya: tampilan kini telah disesuaikan dengan banner sesuai permintaan pengguna. CSS bernonce dan dua aset PNG lokal ditambahkan; laporan di bawah merekam kondisi audit sebelum penyegaran UI tersebut. Pengujian aset/CSP tambahan tersedia di `test_ui.py`.

Tanggal: 17 September 2026. Lingkungan: Windows, Python 3.12, Flask 3.1.3, Werkzeug 3.1.8, Requests 2.34.2, Jinja2 3.1.6. Daftar versi lengkap dan hasil `pip check` ada di `audit/dependencies.txt`.

Audit mencakup `app.py`, `templates/index.html`, `test_app.py`, `requirements.txt`, `README.md`, dan `.env.example`. Asumsi deployment adalah **satu pengguna lokal, satu proses**, berdasarkan launcher yang bind ke `127.0.0.1:8000` dan README awal. Ini bukan asumsi bahwa aplikasi sudah layak menjadi layanan publik. HTML polos dan Python tetap dipertahankan; tidak ada dependency runtime baru, database, atau framework frontend.

Kelas kegagalan yang direproduksi telah diperbaiki dan diuji. Hasil ini tidak membuktikan aplikasi bebas bug atau filter identitas tidak mungkin dilewati.

## Bukti dan cara mengulang

Kode sebelum audit disimpan di `audit/baseline/`, tanpa `.env` atau kredensial. Workspace saat audit bukan repository Git, sehingga pembandingnya adalah snapshot tersebut, bukan commit Git. `.gitignore` sudah mengecualikan `.env`.

| Pemeriksaan | Hasil teramati | Bukti |
| --- | --- | --- |
| 22 test asli pada kode sebelum audit | 22 lulus, 0 gagal/error/skip; pengulangan terakhir 0,061 detik | `audit/original_tests_before.txt` |
| 29 test audit terhadap snapshot lama | 30 assertion failure termasuk subtest, 1 error; sebagian kasus sudah lulus | `audit/regressions_before.txt` |
| Suite setelah perbaikan | **51 lulus, 0 gagal/error/skip**, 1,187 detik | `audit/tests_after.txt` |
| JavaScript sebelum perbaikan | Gagal pada batas 4.000 emoji | `audit/frontend_before.txt` |
| Review lanjutan whitespace frontend | Gagal pada NEL/control separator sebelum penyamaan dengan Python | `audit/frontend_whitespace_before.txt` |
| JavaScript final | **10 pemeriksaan lulus** | `audit/frontend_after.txt` |
| Dependency terpasang | `No broken requirements found.` | `audit/dependencies.txt` |

Jumlah failure bukan jumlah bug independen. Suite tambahan juga menguji batas baru yang memang belum ada pada baseline, misalnya limiter dan autentikasi form. Satu error pada baseline berasal dari test yang mencoba membaca jawaban dari riwayat yang ternyata telah hilang.

```powershell
# Dari direktori proyek, tanpa memakai kuota provider:
.\.venv\Scripts\python audit/run_regressions.py --baseline --original
.\.venv\Scripts\python audit/run_regressions.py --baseline
.\.venv\Scripts\python -m unittest -v
node test_frontend.cjs audit/baseline/index.html
node test_frontend.cjs
.\.venv\Scripts\python -m pip check

# Profil CPU, jalankan berurutan agar tidak saling membebani:
.\.venv\Scripts\python audit/profile_app.py --baseline
.\.venv\Scripts\python audit/profile_app.py

# Opsional, mengakses provider nyata:
.\.venv\Scripts\python audit/profile_app.py --network
.\.venv\Scripts\python audit/profile_chat.py --live
```

Test provider memakai mock, kecuali test pooling yang memakai server HTTP lokal dengan key sintetis. Dua perintah profil terakhir menggunakan konfigurasi lokal: `--network` mengukur GET metadata; `--live` mengirim dua prompt sintetis dan menggunakan kuota gratis. Jangan menjalankan server dari snapshot baseline sebagai aplikasi sehari-hari.

## A. Keamanan

### A1 — BUG NYATA: riwayat assistant dapat dipalsukan

**Dampak sedang pada integritas percakapan.** Sebelumnya client dapat mengganti isi assistant di hidden input dan server meneruskannya sebagai riwayat assistant. Ini tidak membuktikan pengambilalihan komputer atau kebocoran lintas pengguna; client pada dasarnya memalsukan konteks percakapannya sendiri, tetapi melampaui jalur input user yang dimaksud aplikasi.

Reproduksi: kirim satu pesan, parse form respons, ganti `history[-1].content`, pertahankan field lain, lalu kirim pesan berikutnya. `test_forged_assistant_history_is_rejected` dahulu menerima request; sekarang HTTP 400 tanpa panggilan API kedua. `sign_history` (`app.py:301`) menandatangani JSON canonical menggunakan HMAC-SHA256 dan mengikatnya ke token sesi. Test `test_missing_csrf_and_cross_session_history_are_rejected` juga membuktikan riwayat bertanda tangan tidak dapat dipindahkan ke sesi lain.

**Hasil pemeriksaan role: aman untuk kasus yang diuji, sejak baseline.** `system`, `tool`, urutan assistant/user yang salah, object pengganti list, isi non-string, jumlah ganjil, dan index edit assistant ditolak. Tidak ditemukan bypass role pada corpus test. Extra field tidak diteruskan ke provider. HMAC menambah autentisitas, tidak menggantikan validasi role atau filter assistant.

**RISIKO POTENSIAL tersisa:** user masih dapat menulis instruksi berbahaya dalam pesan user yang sah. HMAC tidak menyelesaikan prompt injection pada LLM. Form autentik dari sesi yang sama juga dapat dikirim ulang; ini sengaja memungkinkan Back/edit, dengan limiter sebagai pembatas kuota. Tanda tangan tidak mengenkripsi riwayat.

### A2 — BUG NYATA: validasi riwayat tidak konsisten dengan batas aplikasi

**Dampak rendah–sedang.** `read_history` lama menerima pesan user 4.001 karakter sampai 20.000 karakter, tidak membatasi total 12.000 karakter saat membaca, dan menerima lone surrogate. Payload JSON dengan 10.000 tingkat nesting masuk jalur RuntimeError/503, bukan validasi input/400. Keberadaan input tidak valid terbukti; tidak diklaim pernah dikirim oleh pengguna nyata.

Bukti: `test_history_rejects_lone_surrogates_and_oversized_user_messages`, `test_context_and_request_body_limits`, `test_deep_json_history_returns_400_instead_of_runtime_error`. Sekarang `valid_text`/`read_history` (`app.py:266`, `app.py:271`) membatasi user 4.000, assistant 8.000, total 12.000 code point, maksimal 20 pesan genap, menolak surrogate, dan mengubah kegagalan nesting menjadi HTTP 400.

History kosong dengan `edit=0` atau `edit_index=0`, index negatif/ganjil/di luar array, emoji, RTL campuran, dan combining mark juga diuji. Tidak ada alasan untuk menolak RTL atau emoji valid. Batas memakai code point, bukan byte atau grapheme cluster. Contoh `e` + combining acute dihitung dua; ini semantik yang kini dijelaskan, bukan bug Unicode tersendiri.

### A3 — BUG NYATA: pesan Unicode valid dapat gagal di browser/form

**Dampak sedang pada fungsi chat.** Backend menghitung code point, sedangkan `maxlength=4000` lama menghitung unit UTF-16. Sebanyak 4.000 emoji tidak bisa dikirim melalui jalur browser tersebut. Selain itu, form default URL-encoded dengan JSON ASCII escape membengkak: riwayat sintetis valid 4.000 emoji user + 8.000 emoji assistant menyebabkan POST berikutnya HTTP 413 meskipun masih dalam batas 12.000 karakter aplikasi.

Bukti: `test_frontend.cjs` terhadap HTML baseline dan `test_browser_form_round_trip_at_emoji_limits`. Sekarang HTML menghitung code point dalam JavaScript, menggunakan form multipart dan JSON UTF-8. Batas body 128 KiB **tidak dinaikkan**. Backend tetap menjadi validasi wajib ketika JavaScript dimatikan. Kombinasi riwayat valid 12.000 code point dan draf 4.000 code point memerlukan paling banyak sekitar 64 KiB UTF-8 sebelum overhead form; test round-trip memakai kasus emoji empat byte.

Review lanjutan juga membuktikan `String.trim()` berbeda dengan `str.strip()` Python untuk NEL/control separator dan BOM. Pemeriksaan whitespace tepi frontend disamakan dengan pemindaian linear; dua pemeriksaan tambahan menangkap batas tersebut. Ini tercatat sebagai koreksi pada implementasi hardening awal, bukan disembunyikan sebagai kegagalan produksi lama.

### A4 — BUG NYATA: beberapa encoding/homoglyph melewati filter identitas

**Dampak pada kebijakan identitas produk, bukan akses kredensial.** Input `GΡΤ` dengan rho/tau Yunani, HTML entity dua lapis, Unicode escape berbentuk `\u{47}\u{50}\u{54}`, Base64 satu kalimat yang memuat nama model, dan Base64 bertingkat melewati filter lama. `test_additional_encoding_and_greek_homoglyph_bypasses` menunjukkan kegagalan sebelum fix dan penggantian ke jawaban Meteor sesudahnya.

Perbaikan: normalisasi URL/HTML/Unicode escape berulang maksimal tiga putaran, tambahan confusable yang direproduksi, serta decoding Base64 kandidat maksimal tiga tingkat, 32 kandidat yang diperiksa, dan 32 token per kandidat. Semua alias serta marker lama untuk kapitalisasi, tanda baca, zero-width, diakritik, hex, ROT13, dan terbalik tetap dipertahankan. Test lama filter dan penyaringan sebelum render/history tetap lulus.

**RISIKO POTENSIAL tersisa:** ini filter nama yang diketahui, bukan pembuktian semua representasi informasi. Encoding lain, penyandian lebih dalam, acrostic lintas jawaban, atau homoglyph yang belum dipetakan masih perlu corpus adversarial tersendiri. False positive pada pembahasan umum nama provider/model juga mungkin. Model yang berbeda kelak membutuhkan pembaruan alias. Tidak ada janji “tidak pernah bocor” melalui prompt saja.

### A5 — BUG NYATA: exception tak terduga bisa dipantulkan mentah

**Dampak sedang bila exception berisi data sensitif.** Test menyuntikkan `RuntimeError` berisi sentinel; baseline menampilkan sentinel pada halaman lewat `except RuntimeError: str(exc)`. Ini membuktikan refleksi pesan exception, **bukan** bukti key nyata pernah bocor dari provider. RecursionError provider juga termasuk keluarga RuntimeError.

`test_unexpected_exception_does_not_expose_message_or_traceback` kini mendapat HTTP 500 generik, tanpa sentinel di response maupun argumen log. Pesan operasional yang aman memakai `ChatError` khusus; exception lain hanya dicatat nama kelasnya (`app.py:374` dan penanganan dalam route). Draf/riwayat sah tetap ada untuk kegagalan di route.

**Hasil pemeriksaan error provider: aman pada jalur yang diuji.** HTTP error body, reasoning, usage, dan metadata tidak ditampilkan atau dicatat; `test_provider_errors_and_metadata_do_not_leak_to_page_or_app_logs` memakai sentinel. Tidak ada endpoint file `.env`/source; test lama untuk kredensial tetap lulus. Log nomor key bukan isi key.

**RISIKO POTENSIAL:** access log server dapat memuat teks sensitif jika ada di query URL, meski aplikasi tidak memerlukannya. Launcher kini menyetel logger Werkzeug ke ERROR; `test_launcher_suppresses_access_queries_and_declares_threading` memverifikasi kebijakan launcher. Konfigurasi log reverse proxy/WSGI eksternal dan telemetry provider tidak diaudit sebagai bagian proses lokal ini. Jangan mengartikan sanitasi logger aplikasi sebagai kendali atas semua sistem eksternal.

### A6 — RISIKO POTENSIAL: request lintas origin dan Host tak dikenal

**Skenario lokal konkret:** pengguna membuka halaman berbahaya yang mencoba mengirim form ke localhost dan menghabiskan kuota. Baseline menerima POST lintas origin dan Host sembarang pada Flask test client. Eksploitasi browser end-to-end melalui situs berbahaya tidak diuji; Private Network Access dan kebijakan browser dapat memengaruhinya. Karena itu tidak diklaim ada serangan jarak jauh yang sudah terjadi.

Sekarang POST memerlukan token CSRF yang diikat cookie, pemeriksaan Origin/`Sec-Fetch-Site`, dan tanda tangan riwayat. Cookie HttpOnly/SameSite=Strict; host dibatasi ke localhost/loopback. Bukti: `test_cross_origin_post_does_not_reach_provider`, `test_untrusted_host_is_rejected`, dan test missing-CSRF/cross-session. Origin yang tidak dikirim tetap memerlukan token dan tanda tangan. Risiko aplikasi lokal lain yang dapat membaca cookie/secret tidak diselesaikan oleh CSRF. Rancangan mengikuti kontrol yang dibahas dalam [dokumentasi keamanan Flask](https://flask.palletsprojects.com/en/stable/web-security/).

**BUG NYATA pada review hardening awal, sudah ditutup:** parsing `Origin: http://[` sempat menghasilkan 500 dan secret eksplisit yang pendek belum ditolak. `audit/followup_before.txt` mencatat dua test merah. Pemeriksaan Origin kini memakai pencocokan string origin tepat; startup menolak secret nonkosong di bawah 32 byte tanpa mencetak nilainya. Test terkait: `test_malformed_origin_is_a_client_error_without_provider_call`, `test_weak_explicit_signing_secret_is_rejected_without_echoing_it`. Panjang minimum tidak membuktikan entropi; secret acak tetap harus dibuat dengan generator aman. Default kosong memakai `secrets.token_hex(32)`.

### A7 — CSP dan HTML: aman untuk payload yang diuji

Tidak ditemukan bypass pada payload HTML yang direproduksi. Template menampilkan teks melalui escaping Jinja, termasuk nilai attribute history. Payload penutup textarea, `formaction`, `onclick`, dan `onerror` tetap berupa teks; `test_markup_is_escaped_including_formaction_and_event_handlers` memeriksanya. Tidak ada penggunaan `innerHTML`, HTML dari model, atau event handler inline dalam template.

CSP tetap `default-src 'none'`, nonce script unik per respons, `form-action 'self'`, `frame-ancestors 'none'`, `base-uri 'none'`. Tidak ditambahkan `unsafe-inline`. Test nonce lama tetap lulus; header juga disetel pada response error. `Cache-Control: no-store` dan `nosniff` dipertahankan. CSP membatasi aksi form, tetapi tidak menggantikan CSRF. Secure cookie/HSTS tidak diaktifkan pada HTTP loopback; layanan HTTPS publik membutuhkan konfigurasi itu. Ketiadaan HSTS pada target lokal ini bukan bug kritis.

### A8 — RISIKO POTENSIAL: abuse dan pemakaian memori

Pada single-user lokal, pembatas per IP kurang berguna karena semua tab berasal dari loopback. Pada layanan publik tanpa autentikasi, siapa saja dapat menghabiskan kuota. Kini ada pembatas sederhana **20 pengiriman valid per menit per proses**, termasuk kegagalan provider; request ke-21 mendapat 429 dan Retry-After tanpa panggilan provider. GET, Edit/Batal tanpa regenerasi tidak memakai kuota ini. Test `test_local_request_budget_returns_429_without_more_provider_calls` membuktikan batas baru.

Body request tetap 128 KiB; batas form memory juga 128 KiB dan multipart maksimal 12 bagian. `test_excess_multipart_parts_are_rejected_before_provider_call` menghasilkan 413 untuk 13 field tambahan sebelum memakai API. `MAX_FORM_MEMORY_SIZE` adalah pagar parser yang selaras dengan batas body, bukan klaim batas total RAM proses. Request terlalu besar mendapat 413; jangan menjanjikan pemulihan seluruh history dari body yang memang tidak diterima.

Limiter dan lock tidak membatasi jumlah semua koneksi/GET/thread, tidak mengenali pengguna publik, dan tidak dibagi antar worker. Flood koneksi lambat tetap memerlukan pembatas server/proxy. Risiko ini tersisa dan sengaja didokumentasikan; aplikasi tidak diekspos ke internet selama audit.

## B. Ketahanan OpenRouter/Groq

### B1 — BUG NYATA: beberapa error schema menghentikan fallback

**Dampak sedang pada ketersediaan.** HTTP 200 dengan `error.code = Infinity` memicu OverflowError ketika dikonversi ke int; JSON provider sangat dalam memicu RecursionError. Baseline tidak mencoba key sehat berikutnya. `test_embedded_infinite_error_code_falls_back` dan `test_deep_provider_json_falls_back` sekarang membuktikan fallback berhasil. Python JSON menerima token Infinity secara default; ini reproduksi respons rusak, bukan klaim provider resmi sengaja mengirimnya.

Penanganan diperluas untuk OverflowError/RecursionError. Schema/list/tipe yang salah, isi kosong, dan model tak sesuai tetap ditolak. Redirect tetap tidak diikuti. TLS verification tidak dimatikan.

### B2 — BUG NYATA: Retry-After dapat menonaktifkan key tanpa batas

`Retry-After: inf`/`1e309` menghasilkan jeda tak finite pada baseline; `1e100` dan HTTP date tahun 9999 menghasilkan jeda tidak praktis. Bukan semua input aneh menghasilkan nol/negatif: baseline sudah meng-clamp banyak kasus ke minimal satu detik. Perbaikan membatasi hasil finite 1–86.400 detik, non-finite/format rusak memakai fallback 60 detik atau 3.600 untuk 401/402/403.

Bukti: `test_retry_after_is_finite_and_bounded`, test HTTP date lama, dan `test_retry_defaults_and_elapsed_cooldown_recovery`. Waktu tunggu internal berpindah dari wall clock ke monotonic agar koreksi jam sistem tidak menggeser cooldown. HTTP date tetap dihitung dari waktu UTC saat header diterima.

### B3 — BUG NYATA: jawaban panjang bisa menghilangkan turn terbaru

Baseline menerima content lebih dari 12.000 karakter lalu `trim_history` menghapus seluruh pasangan, termasuk pesan baru dan jawabannya. Halaman dapat kembali tanpa jawaban dan tanpa error. `test_oversized_answer_cannot_silently_erase_conversation` mereproduksi history kosong dengan jawaban sintetis 12.001 karakter. Sekarang jawaban di atas 8.000 ditolak dan masuk fallback; satu user maksimum 4.000 + assistant maksimum 8.000 selalu dapat dipertahankan sebagai pasangan terbaru.

### B4 — RISIKO POTENSIAL: body provider besar atau rangkaian timeout panjang

Sebelumnya `.json()` menerima seluruh body tanpa batas aplikasi. Test respons dengan metadata 140.000 karakter membuktikan tidak ada penolakan ukuran; tidak dilakukan eksperimen menghabiskan RAM. Kini `read_provider_json` (`app.py:188`) menampung maksimum 128 KiB setelah decoding HTTP dan menutup response dalam `finally`. Test `test_response_size_is_bounded_and_connections_are_closed` membuktikan penolakan/fallback serta penutupan koneksi sukses/gagal.

Enam timeout berturut-turut dahulu tetap memulai enam percobaan. Sekarang ada anggaran elapsed lunak 45 detik. Test jam sintetis yang menaikkan waktu 20 detik per timeout membuktikan tidak ada percobaan keempat; percobaan ketiga dapat selesai sekitar 60 detik. **45 detik bukan hard deadline.** Connect/read timeout bukan pengukur total wall clock; DNS, beberapa alamat IP, atau pengiriman data sedikit demi sedikit dapat melampauinya. [Dokumentasi Requests](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts) menjelaskan semantik ini.

**RISIKO POTENSIAL tersisa:** respons lambat atau dekompresi pathological dapat memakai waktu/memori di lapisan requests/urllib3 sebelum kontrol kembali ke aplikasi. Batas buffer bukan batas RAM keras seluruh HTTP stack. Tidak ada reproduksi provider nyata untuk kondisi itu; jaminan deadline keras membutuhkan isolasi/proses atau transport lain, sehingga tidak ditambahkan secara spekulatif ke aplikasi minimal ini.

### B5 — RISIKO POTENSIAL: state key antar thread/worker

Premis bahwa `app.run` saat ini single-threaded secara default **tidak benar pada Flask terpasang**. Inspeksi `Flask.run` menemukan `options.setdefault("threaded", True)`, sesuai [dokumentasi Flask](https://flask.palletsprojects.com/en/stable/api/#flask.Flask.run). Baseline tidak menimpanya.

`test_parallel_requests_do_not_call_a_busy_key_twice` menggunakan dua thread dan Event untuk mereproduksi dua panggilan API yang tumpang tindih pada key sama. Test itu membuktikan overlap; tidak diklaim sudah membuktikan kerusakan state tertentu. Interleaving pembaruan `active_key`/`retry_at` bisa memberi pemilihan key/cooldown yang tidak konsisten.

Kini lock nonblocking melindungi seluruh pemilihan key, jaringan, cooldown, limiter, dan Session. Request kedua mendapat pesan sibuk 503/Retry-After=1; halaman GET tetap bisa dilayani oleh thread server. Lock dilepas dalam `finally`. **Beberapa worker tetap mempunyai state berbeda**; default secret acak per proses juga membuat cookie antar worker tidak cocok. Multi-worker belum didukung sebagai deployment publik. Tidak ada klaim global state lintas proses kini aman.

### B6 — Matriks error dan graceful degradation

`test_http_and_schema_failure_matrix` menguji 26 skenario fallback: redirect 301; HTTP 400, 401, 402, 403, 408, 429, 500, 502, 503, 504; ConnectTimeout, ReadTimeout, ConnectionError, SSLError, ChunkedEncodingError; top-level list/string/int, error object tak sesuai, model null, choices null/kosong bentuknya, content hilang/list/whitespace. Invalid JSON dan error embedded 429 juga tetap dicakup test lama.

HTTP non-200 lainnya memakai cabang gagal yang sama, tetapi tidak diklaim setiap status numerik telah diuji satu-satu atau seluruh kegagalan transport OS terenumerasi. Tidak ada panggilan API nyata untuk memaksa outage/401. Skenario mock memverifikasi respons aplikasi terhadapnya.

Semua key gagal, semua sedang cooldown, atau tidak ada key aktif menghasilkan 503 dengan pesan yang jelas. Draf dan history sah dipertahankan untuk retry; edit yang gagal mempertahankan history lama serta draf edit. Test lama dan `test_all_cooling_keys_fail_clearly_without_network` lulus. Tidak ditemukan silent failure selain jawaban panjang B3 yang sudah diperbaiki.

Model tetap dipin, harga OpenRouter input/output/request tetap nol, dan key Groq tetap memerlukan konfirmasi Free Plan. Test lama tetap memverifikasi payload tersebut. Enam key bisa berbagi kuota akun/organisasi, jadi perpindahan key bukan penambahan kuota yang dijamin. Lihat [batas OpenRouter](https://openrouter.ai/docs/api_reference/limits) dan [batas Groq](https://console.groq.com/docs/rate-limits).

## C. Pengukuran dan keputusan performa

### Profil lokal yang dapat diulang

`audit/profile_app.py` memakai `perf_counter`, satu warm-up dan 200 pengulangan per fungsi, tanpa jaringan. History fixture: 20 pesan, masing-masing 600 karakter, total 12.000. Sebelum/sesudah dijalankan berurutan, tidak bersamaan dengan suite test. Hasil di `audit/profile_before_local.json` dan `audit/profile_after.json`. Waktu adalah wall time, dapat dipengaruhi scheduler; bukan benchmark lintas mesin.

| Operasi | Median sebelum (ms) | Median sesudah (ms) | p95 sesudah (ms) |
| --- | ---: | ---: | ---: |
| GET halaman kosong | 0,2307 | 0,3905 | 0,5648 |
| read_history 12.000 karakter / 20 pesan | 0,6618 | 1,5542 | 2,6397 |
| trim_history dengan tambahan 4.000 karakter | 0,0078 | 0,0076 | 0,0078 |
| Filter identitas 8.000 karakter | 0,6764 | 0,7084 | 0,8360 |
| Render history 12.000 karakter / 20 pesan | 0,2816 | 0,3860 | 0,6598 |

Validasi dan penandatanganan menambah biaya CPU. Tidak diklaim semua bagian menjadi lebih cepat. Fixture berulang `a` bukan worst-case seluruh encoding; batas kandidat mencegah pencarian decoder tanpa akhir.

### Chat nyata dan lokasi bottleneck

`audit/profile_chat.py --live` membungkus `Session.post` sampai header dan pembacaan body, kemudian mengukur total POST Flask test client. Dua pesan sintetis, konfigurasi key nyata, tanpa mencetak key/prompt/answer. Hasil `audit/profile_chat.json`:

| Pesan | Total (ms) | Pemanggilan provider + baca/decode (ms) | Pekerjaan lainnya (ms) | Hasil |
| --- | ---: | ---: | ---: | --- |
| 1 | 2.274,80 | 2.271,00 | 3,80 | 429 pada key pertama, lalu 200 pada berikutnya |
| 2 | 381,62 | 376,45 | 5,17 | 200, memakai key sukses |

Sekitar 98,6–99,8% waktu terukur berada pada pemanggilan provider/pembacaan. Pengukuran ini mencakup jaringan, antrean/inferensi provider dan sedikit serialisasi/decode client; tidak dapat memisahkan semuanya tanpa telemetry provider. Sampel dua bukan estimasi SLA, p95 produksi, atau perbandingan kualitas model. Ini cukup untuk mengarahkan optimasi ke transport, bukan micro-optimasi Jinja.

### Pooling: OPINI/PREFERENSI GAYA — pilihan optimasi, bukan perbaikan bug

Penggunaan Session bersifat opsional secara desain, tetapi dipilih di sini berdasarkan eksperimen. `audit/profile_app.py --network` mengukur GET metadata dengan tiga fresh connection dan tiga pooled request per provider, urutan interleaved. Semua HTTP 200; percobaan pooled pertama masih cold. Data mentah di `audit/profile_before.json`:

| Provider | Median fresh (ms) | Median pooled (ms) |
| --- | ---: | ---: |
| OpenRouter | 378,83 | 68,17 |
| Groq | 616,37 | 306,35 |

Ada indikasi penghematan setup sekitar 310 ms pada pola request berdekatan ke host sama, **bukan** jaminan chat akan lebih cepat sebesar itu. Endpoint metadata tidak melakukan inferensi. Jeda pengguna yang panjang atau penutupan keep-alive oleh server mengurangi manfaatnya.

Trade-off Session: koneksi/state hidup lebih lama, cookie perlu diisolasi, akses thread perlu dikendalikan, dan streamed response harus dikonsumsi atau ditutup. Implementasi membersihkan cookie, mengirim Authorization per request, serialisasi akses dengan lock, menutup setiap response dan Session saat proses berakhir. Test HTTP lokal `test_connection_is_reused_without_sharing_cookies_or_authorization` membuktikan port TCP client yang sama pada dua request, header auth berbeda sesuai key, dan tidak ada cookie menyeberang. Cara pooling/pelepasan response juga dijelaskan pada [dokumentasi Session Requests](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects).

### Timeout dan kompleksitas

**OPINI/PREFERENSI GAYA — opsional:** pemisahan timeout per provider belum mempunyai data p95/p99 inferensi yang memadai. Nilai maksimum `(5, 20)` dipertahankan, diperkecil jika sisa anggaran kurang. Dua chat singkat dan GET metadata tidak membenarkan kesimpulan provider tertentu selalu cepat/lambat. Tuning berikutnya perlu sampel berulang untuk prompt pendek/panjang dan jam berbeda, tanpa mencatat isi prompt ke log operasional.

Untuk `H` pesan dan `C` total karakter: `trim_history` menggunakan slicing awal, lalu penjumlahan panjang dan slicing ulang per pasangan. Worst-case **O(H²)** waktu dan **O(H)** peak referensi list tambahan; `len(str)` tidak memindai ulang karakter. Pada H=20, penjumlahan maksimum 20+18+...+2=110 kunjungan. Kode ini tidak diubah karena waktu terukur sekitar 0,008 ms. **OPINI/PREFERENSI GAYA — opsional:** versi running-total O(H) berguna bila batas meningkat jauh; bukan temuan bug saat ini.

Render Jinja, escaping, pemecahan baris, serialisasi JSON dan HMAC adalah **O(C+H)** dengan ukuran output sebanding input. Validasi history menambah pemeriksaan string/filter; filter memiliki faktor jumlah marker dan kandidat, secara kasar O(K·M·C), dengan K dibatasi 32 dan M berasal dari alias tetap. Tidak ada ledakan jumlah putaran decode tak berbatas. Memory template/JSON tetap proporsional data yang dirender, bukan penyimpanan seluruh chat tanpa batas.

## D. Korektnes, maintainability, dan dokumentasi

### Proteksi test lama tetap dipertahankan

Tidak ada satu pun dari 22 test lama yang dihapus. Penyesuaian fixture diperlukan karena transport kini `app.http.post`, pembacaan body streaming, clock cooldown monotonic, dan form wajib autentik. Fixture test flow dibuat seperti form server yang sah dengan HMAC/token. Test khusus pemalsuan tidak memakai cara pintas itu. Test lama untuk history assistant berbahaya masih menguji sanitizer pada fixture bertanda tangan agar jalur legacy tetap dilindungi; history palsu tanpa signature sekarang sengaja ditolak.

RuntimeError operasional berubah menjadi `ChatError` agar route hanya menampilkan pesan yang sengaja ditulis aplikasi. Test diperbarui ke exception tersebut. Fallback sampai enam key masih diuji dengan kegagalan cepat; batas waktu baru hanya menghentikan rangkaian yang sudah kehabisan anggaran. CSP nonce, model canonical/free, rejection model moderasi, penjelasan sah tentang label safety, escaping, edit/regenerate/cancel, dan preservasi draf saat gagal tetap lulus.

**BUG NYATA pada konsistensi dokumentasi sebelumnya**, berikut baris pembanding yang tetap dapat dilihat di snapshot:

| README lama di `audit/baseline/README.md` | Kode lama yang bertentangan / tidak mencakup klaim | Penyelesaian |
| --- | --- | --- |
| Baris 31: satu pesan maksimal 4.000 karakter | `audit/baseline/app.py:184` menerima user history sampai 20.000; `audit/baseline/index.html:29` memakai maxlength UTF-16 | A2/A3; README sekarang baris 37 menjelaskan code point dan batas per role |
| Baris 31: maksimum 12.000 karakter dipertahankan | `audit/baseline/app.py:172` tidak membatasi total saat read; cabang Edit/Batal pada baris 220 tidak melakukan trim sehingga history kiriman yang berlebih diterima | read_history menolak total berlebih sebelum edit/cancel |
| Baris 25: kegagalan layanan memicu percobaan key berikutnya | `audit/baseline/app.py:150` OverflowError dan baris 148 RecursionError keluar dari daftar exception yang ditangani | B1; README baris 27–28 kini menyebut schema dan batas waktu |
| Baris 17: key hanya dibaca dari `.env` | `audit/baseline/app.py:22` load_dotenv dan baris 89 getenv juga menerima environment proses | README baris 17 menyebut environment atau `.env` |

Baris 25 tentang fallback Retry-After 60 detik/1 jam sesuai kode lama untuk header hilang/rusak; itu **bukan kontradiksi**. README lama belum menjelaskan input non-finite/tanggal ekstrem; sekarang batas 1–86.400 didokumentasikan. Urutan key/sticky success pada baris 23 juga sesuai, kini diperjelas key invalid/duplikat/cooldown dan batas waktu. Klaim log baris 24 benar untuk warning/info eksplisit aplikasi, tetapi lingkupnya kurang jelas: launcher lama `app.py:265` mengaktifkan logging INFO tanpa pembatasan access log. Ini **RISIKO POTENSIAL dokumentasi**, skenarionya query URL sensitif; bukan bukti logger warning mengeluarkan key. README baru baris 59 menjelaskan batas lingkupnya. Klaim tanpa database, tanpa CSS, dan cara edit pada baris 34 sesuai. Caveat filter bukan jaminan pada baris 43 sudah benar, dipertahankan. Klaim single-thread default berasal dari pertanyaan audit, bukan README; koreksinya di B5.

`README.md` sekarang mencakup sesi/CSRF/HMAC, dampak restart, output/body limits, limiter lokal, threading, timeout lunak, test dan profiling. `.env.example` menambahkan opsi secret tanpa nilai nyata dan menjelaskan generator acak; flag Groq default tetap false. `requirements.txt` diperiksa dan **tidak diubah**. Paket terpasang memenuhi rentang dan `pip check` lulus; tidak dilakukan audit CVE menyeluruh, sehingga hasil itu tidak berarti tidak ada kerentanan dependency. **RISIKO POTENSIAL:** rentang versi memungkinkan instalasi masa depan berbeda; lingkungan deploy baru perlu menjalankan suite lagi. **OPINI/PREFERENSI GAYA — opsional:** lockfile untuk deployment reproducible dapat ditambahkan kemudian, tidak dibutuhkan untuk menutup reproduksi saat ini.

### Verifikasi browser nyata

Setelah menjalankan server baru di loopback, browser in-app diuji dengan percakapan sintetis: Enter menghasilkan jawaban, Shift+Enter menambah baris tanpa submit, pesan kedua mempertahankan turn pertama, edit turn pertama menghasilkan jawaban baru dan membuang turn kedua, serta Batal mempertahankan percakapan. Input 4.000 emoji memberi validity true dan 4.001 memberi validity false. Ini smoke test browser, bukan cakupan semua browser/IME perangkat fisik; skenario IME dan duplicate submit diuji lewat event stub JavaScript.

Pemeriksaan tambahan validity NEL/control separator lewat selector browser tidak konklusif karena alat evaluasi selector mengalami timeout, meskipun textarea masih dapat dibaca dan dikosongkan lewat accessibility. Tidak dihitung sebagai test browser lulus atau bukti aplikasi gagal. Batas whitespace tersebut lulus pada pemeriksaan JavaScript dan backend; batas BOM browser tidak dilanjutkan setelah timeout itu.

Halaman dikembalikan ke Percakapan baru setelah pengujian. API nyata dipakai hanya untuk prompt sintetis singkat dan pengukuran yang disebut di atas. Test failure/error provider menggunakan mock agar audit tidak sengaja menghabiskan kuota atau memaksa outage.

## Batas hasil audit

Risiko tersisa yang konkret: bypass identitas di luar corpus terbatas, prompt injection user yang sah, timeout/dekompresi di lapisan transport, abuse koneksi/GET, state lintas worker, konfigurasi log eksternal, perubahan layanan/kuota gratis, dan dependency versi mendatang. Tidak ada bukti semua kondisi tersebut terjadi sekarang. Konfigurasi final ditujukan untuk penggunaan lokal dengan kegagalan yang dikenali menghasilkan error aman; publikasi sebagai layanan memerlukan audit deployment tambahan.
