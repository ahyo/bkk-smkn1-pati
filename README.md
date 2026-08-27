# Sistem BKK — SMK Negeri 1 Pati

Portal **Bursa Kerja Khusus (BKK)** untuk SMK Negeri 1 Pati: perusahaan mitra memasang lowongan,
alumni melamar dan memantau proses seleksi, serta admin sekolah mengawasi keduanya
sekaligus menyiapkan laporan penyaluran.

Dibangun dengan **FastAPI + Jinja2 + PostgreSQL**, tanpa framework JavaScript
(hanya CSS dan JS ringan) agar mudah dipelihara oleh tim sekolah.

---

## Daftar isi

- [Fitur per peran](#fitur-per-peran)
- [Arsitektur & struktur berkas](#arsitektur--struktur-berkas)
- [Menjalankan secara lokal](#menjalankan-secara-lokal)
- [Menjalankan dengan Docker](#menjalankan-dengan-docker)
- [Akun demo](#akun-demo)
- [Demo GitHub Pages](#demo-github-pages)
- [Konfigurasi](#konfigurasi)
- [Model data](#model-data)
- [Daftar rute](#daftar-rute)
- [Pengujian](#pengujian)
- [Menuju produksi](#menuju-produksi)

---

## Fitur per peran

### 🎓 Pencari kerja (alumni & siswa tingkat akhir)
- Registrasi mandiri dengan NIS, kompetensi keahlian, dan tahun lulus.
- Profil lengkap: data diri, ringkasan, keahlian, riwayat pendidikan & PKL, foto, dan CV.
  Indikator **kelengkapan profil** mendorong pengisian yang utuh.
- Pencarian lowongan dengan filter kata kunci, lokasi, jurusan, tipe kerja, dan pengurutan.
- Kirim lamaran beserta surat lamaran dan CV (memakai CV tersimpan bila tidak diunggah ulang).
- Papan **Lamaran Saya** dengan status, catatan perusahaan, dan jadwal wawancara.
- Simpan lowongan untuk dilamar kemudian; rekomendasi otomatis berdasarkan jurusan.

### 🏢 Perusahaan (DUDI)
- Registrasi mandiri; akun aktif memposting setelah **diverifikasi admin BKK**.
- Profil perusahaan lengkap dengan logo, bidang usaha, alamat, dan PIC —
  tampil pada halaman mitra publik.
- Formulir lowongan menyeluruh: deskripsi, kualifikasi, benefit, jurusan sasaran,
  kuota, rentang gaji (dapat disembunyikan), batas lamaran, dan kriteria kandidat.
- Simpan sebagai **draf** atau kirim untuk ditinjau admin.
- Papan pelamar dengan filter per lowongan, status, dan pencarian keahlian.
- Halaman detail kandidat: profil penuh, surat lamaran, unduh CV, riwayat lamaran,
  pengubahan status seleksi, penjadwalan wawancara, dan catatan untuk pelamar.
- Corong seleksi (funnel) serta statistik tayangan dan pelamar.

### 🛡️ Admin BKK (sekolah)
- Ringkasan seluruh portal: pengguna, mitra, lowongan, lamaran, dan tingkat penerimaan.
- Antrean kerja: verifikasi perusahaan dan persetujuan lowongan langsung dari dashboard.
- Moderasi lowongan dengan catatan yang terbaca oleh perusahaan.
- Kelola pengguna: aktif/nonaktif, reset kata sandi, dan penambahan admin baru.
- Pemantauan seluruh lamaran lintas perusahaan.
- **Laporan & rekap**: lamaran per bulan, rekap per kompetensi keahlian
  (pelamar/lamaran/diterima/persentase), perusahaan paling aktif, ekspor **CSV**, dan tampilan cetak.
- Pengumuman yang tampil di beranda publik.
- Log aktivitas untuk keperluan audit.

---

## Arsitektur & struktur berkas

```
bkk-smk1-pati/
├── app/
│   ├── main.py            # Aplikasi FastAPI, middleware, penanganan galat
│   ├── config.py          # Pengaturan berbasis .env (pydantic-settings)
│   ├── database.py        # Engine & sesi SQLAlchemy
│   ├── models.py          # Model ORM + enum & label bahasa Indonesia
│   ├── security.py        # Hash bcrypt & kebijakan kata sandi
│   ├── deps.py            # Dependency: user aktif, penjaga peran
│   ├── utils.py           # Slug, unggah berkas, format tanggal, paginasi, flash
│   ├── templating.py      # Filter & global Jinja2 terpusat
│   ├── seed.py            # Data contoh realistis
│   ├── routers/
│   │   ├── public.py      # Beranda, daftar & detail lowongan, mitra, tentang
│   │   ├── auth.py        # Masuk, keluar, registrasi, ganti kata sandi
│   │   ├── seeker.py      # Dashboard pencari kerja
│   │   ├── company.py     # Dashboard perusahaan
│   │   └── admin.py       # Panel admin, laporan, ekspor CSV
│   ├── templates/         # 27 template Jinja2
│   └── static/
│       ├── css/style.css  # Design system (tanpa framework)
│       ├── js/app.js      # Interaksi ringan
│       └── uploads/       # CV, logo, foto (cv/ logo/ photo/)
├── docs/                  # Demo statis untuk GitHub Pages
│   └── assets/demo.css    # Gaya khusus demo (tidak pernah tertimpa)
├── scripts/
│   ├── smoke_test.py      # Uji asap 52 pemeriksaan
│   └── build_demo_assets.py  # Sinkronkan CSS + ikon ke docs/
├── .github/workflows/     # CI + deploy GitHub Pages
├── docker-compose.yml     # PostgreSQL + aplikasi
└── Makefile               # Perintah pintas
```

**Autentikasi** memakai sesi cookie tertandatangani (`SessionMiddleware`) dengan hash bcrypt.
Akses per peran dijaga oleh dependency `admin_required` / `company_required` / `seeker_required`.
Pengguna yang belum masuk dialihkan ke `/masuk?next=…`.

---

## Menjalankan secara lokal

Prasyarat: **Python 3.11+** dan **PostgreSQL 14+**.

```bash
# 1. Dependensi
make install            # atau: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. Konfigurasi
make env                # menyalin .env.example → .env dengan SECRET_KEY acak

# 3. Basis data
make db                 # membuat role `bkk` dan database `bkk_smkn1pati`

# 4. Data contoh
make reset              # atau: .venv/bin/python -m app.seed --reset

# 5. Jalankan
make run                # http://localhost:8000
```

Dokumentasi API otomatis tersedia di `/api/docs` selama `DEBUG=true`.

---

## Menjalankan dengan Docker

```bash
make env                # pastikan SECRET_KEY sudah terisi di .env
docker compose up -d --build
docker compose exec web python -m app.seed
```

Aplikasi berjalan di `http://localhost:8000`, PostgreSQL dipetakan ke port `5433`
agar tidak bentrok dengan instalasi lokal. Berkas unggahan disimpan pada volume `bkk_uploads`.

---

## Akun demo

Tersedia setelah menjalankan `make reset`:

| Peran | Email | Kata sandi |
|---|---|---|
| Admin BKK | `admin@bkksmkn1pati.sch.id` | `Admin#12345` |
| Perusahaan | `hrd@ptduakelinci.co.id` | `Perusahaan#123` |
| Pencari kerja | `aditya.nugroho@gmail.com` | `Pelamar#123` |

Seluruh akun perusahaan hasil seed memakai kata sandi `Perusahaan#123`,
dan seluruh akun pencari kerja memakai `Pelamar#123`.

> **Ganti kata sandi admin sebelum dipakai produksi** melalui `ADMIN_PASSWORD` di `.env`
> atau menu *Ganti Kata Sandi* setelah masuk.

---

## Demo GitHub Pages

Direktori `docs/` berisi **pratinjau statis** dari portal yang berjalan sepenuhnya di peramban
(data disimpan pada `localStorage`), sehingga pihak sekolah dan calon mitra dapat menelusuri
ketiga dashboard tanpa memasang server.

```bash
make demo               # http://localhost:8080
```

Mengaktifkan di GitHub:

1. `git init && git add . && git commit -m "Sistem BKK SMK N 1 Pati"`
2. Buat repositori di GitHub lalu `git remote add origin …` dan `git push -u origin main`
3. Buka **Settings → Pages → Source: GitHub Actions**

Alur kerja `.github/workflows/pages.yml` akan memeriksa berkas demo lalu menerbitkannya
setiap kali direktori `docs/` berubah.

**Alur penyesuaian sebelum produksi.** Aplikasi adalah sumber kebenaran tampilan; demo
mengikutinya. Setelah mengubah `app/static/css/style.css` atau `app/icons.py`, jalankan:

```bash
python scripts/build_demo_assets.py
```

Perintah itu menyalin design system ke `docs/assets/style.css` dan membangkitkan
`docs/assets/icons.js` dari `app/icons.py`, sehingga yang disetujui sekolah di demo
benar-benar sama dengan yang tayang di produksi. Gaya yang hanya relevan bagi demo
(bilah "Mode Demo", pengalih peran) tinggal di `docs/assets/demo.css` dan tidak
pernah tertimpa. Struktur HTML serta nama kelas pada demo dibuat identik dengan
template Jinja. Rincian ada pada [`docs/README.md`](docs/README.md).

---

## Konfigurasi

Seluruh pengaturan dibaca dari `.env` (lihat `.env.example`):

| Variabel | Keterangan | Bawaan |
|---|---|---|
| `SECRET_KEY` | Kunci penandatangan sesi — **wajib diganti** | — |
| `DATABASE_URL` | URL koneksi PostgreSQL | `postgresql+psycopg2://bkk:bkk@localhost:5432/bkk_smkn1pati` |
| `APP_ENV` | `development` / `staging` / `production` | `development` |
| `DEBUG` | Mengaktifkan `/api/docs` | `true` |
| `MAX_UPLOAD_MB` | Batas ukuran unggahan | `5` |
| `REQUIRE_JOB_APPROVAL` | Lowongan wajib disetujui admin | `true` |
| `REQUIRE_COMPANY_VERIFICATION` | Perusahaan wajib diverifikasi | `true` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Akun admin awal untuk seeder | — |

Identitas sekolah (nama, alamat, telepon, surel) diatur pada `app/config.py`
dan otomatis dipakai di seluruh halaman serta footer.

Daftar kompetensi keahlian ada pada konstanta `MAJORS` di `app/models.py` —
sesuaikan dengan jurusan yang benar-benar dibuka sekolah.

---

## Model data

| Tabel | Isi |
|---|---|
| `users` | Akun tunggal untuk tiga peran (`admin`, `company`, `seeker`) |
| `companies` | Profil perusahaan + status verifikasi |
| `seekers` | Profil pencari kerja, CV, keahlian |
| `jobs` | Lowongan beserta status moderasi & statistik tayangan |
| `applications` | Lamaran, status seleksi, catatan, jadwal wawancara |
| `saved_jobs` | Lowongan yang ditandai pencari kerja |
| `announcements` | Pengumuman BKK di beranda |
| `activity_logs` | Jejak audit ringan |

Skema dibuat otomatis saat aplikasi dijalankan (`Base.metadata.create_all`).
Alembic sudah terpasang pada `requirements.txt` bila kelak diperlukan migrasi bertahap.

---

## Daftar rute

**Publik** — `/` · `/lowongan` · `/lowongan/{slug}` · `/perusahaan-mitra` ·
`/perusahaan-mitra/{slug}` · `/tentang` · `/health`

**Autentikasi** — `/masuk` · `/keluar` · `/daftar` · `/daftar/pencari-kerja` ·
`/daftar/perusahaan` · `/akun/kata-sandi`

**Pencari kerja** — `/pelamar` · `/pelamar/profil` · `/pelamar/lamaran` ·
`/pelamar/tersimpan` · `/pelamar/lamar/{job_id}` · `/pelamar/simpan/{job_id}`

**Perusahaan** — `/perusahaan` · `/perusahaan/profil` · `/perusahaan/lowongan` ·
`/perusahaan/lowongan/baru` · `/perusahaan/lowongan/{id}/ubah` · `/perusahaan/pelamar` ·
`/perusahaan/pelamar/{id}`

**Admin** — `/admin` · `/admin/perusahaan` · `/admin/lowongan` · `/admin/lamaran` ·
`/admin/pengguna` · `/admin/laporan` · `/admin/laporan/ekspor` · `/admin/pengumuman` · `/admin/log`

---

## Pengujian

```bash
make test          # 52 pemeriksaan: rute publik, ketiga peran, penjaga akses, validasi formulir
node --check docs/assets/demo-app.js   # sintaks demo statis
```

CI pada `.github/workflows/ci.yml` menjalankan uji asap terhadap layanan PostgreSQL
di setiap push dan pull request.

---

## Menuju produksi

1. **Ganti `SECRET_KEY`** dan kata sandi admin bawaan.
2. Setel `APP_ENV=production` dan `DEBUG=false` — dokumentasi API otomatis dinonaktifkan
   dan cookie sesi dipaksa `Secure`.
3. Jalankan di belakang reverse proxy (Nginx/Caddy) dengan **HTTPS**;
   uvicorn sudah dijalankan dengan `--proxy-headers`.
4. Pindahkan direktori unggahan ke volume atau penyimpanan objek yang dicadangkan berkala.
5. Jadwalkan **backup PostgreSQL** harian (`pg_dump`).
6. Pertimbangkan penambahan pengiriman surel (notifikasi status lamaran) dan
   pembatasan laju (rate limit) pada endpoint masuk dan registrasi.
7. Sesuaikan daftar `MAJORS` dan identitas sekolah pada `app/config.py`.

---

© BKK SMK Negeri 1 Pati.
