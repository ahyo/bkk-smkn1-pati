# Demo GitHub Pages — Portal BKK SMK Negeri 1 Pati

Folder ini berisi **pratinjau statis** dari aplikasi FastAPI di direktori `app/`.
Tujuannya agar pihak sekolah dan calon mitra dapat menelusuri seluruh alur portal —
termasuk ketiga dashboard — tanpa perlu memasang server dan PostgreSQL.

## Cara kerja

| Aspek | Aplikasi produksi (`app/`) | Demo (`docs/`) |
|---|---|---|
| Backend | FastAPI + SQLAlchemy | tidak ada (murni peramban) |
| Basis data | PostgreSQL | `localStorage` peramban pengunjung |
| Template | Jinja2 | template literal JavaScript |
| Autentikasi | bcrypt + sesi cookie | pengalih peran satu klik |
| CSS | `app/static/css/style.css` | `docs/assets/style.css` (salinan + tambahan demo) |

Struktur HTML dan nama kelas CSS sengaja dibuat identik, sehingga penyesuaian
tampilan yang disetujui pada demo dapat langsung dipindahkan ke template Jinja.

## Menjalankan secara lokal

```bash
python3 -m http.server 8080 --directory docs
# buka http://localhost:8080
```

## Menyalin perubahan tampilan ke produksi

Bila hanya CSS yang berubah:

```bash
cp docs/assets/style.css app/static/css/style.css
# lalu hapus blok "Tambahan khusus demo GitHub Pages" di bagian akhir berkas
```

Perubahan struktur halaman perlu diterapkan manual pada template Jinja terkait
(`app/templates/...`), karena penanda `{{ }}` tidak ada pada versi demo.

## Menyetel ulang data demo

Tombol **↺ Reset data** pada bilah kuning di bagian atas halaman mengembalikan
seluruh data ke kondisi awal (`assets/demo-data.js`).
