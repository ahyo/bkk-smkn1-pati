#!/usr/bin/env python3
"""Uji asap: menelusuri seluruh rute penting portal untuk ketiga peran.

Jalankan setelah `python -m app.seed --reset`:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Application, Company, CompanyStatus, Interest, Job, JobStatus, Major, Role, Seeker, User,
)

OK, GAGAL = [], []


def cek(label: str, kondisi: bool, detail: str = "") -> None:
    (OK if kondisi else GAGAL).append(label)
    tanda = "  ✓" if kondisi else "  ✗"
    print(f"{tanda} {label}" + (f" — {detail}" if detail and not kondisi else ""))


def get(client: TestClient, url: str, harap: int = 200) -> None:
    # follow_redirects dimatikan agar pengalihan 303 (penjaga akses) dapat diuji apa adanya.
    r = client.get(url, follow_redirects=False)
    cek(f"GET {url}", r.status_code == harap, f"status {r.status_code}")


def main() -> int:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.status == JobStatus.PUBLISHED).first()
        comp = db.query(Company).filter(Company.status == CompanyStatus.VERIFIED).first()
        comp_user = db.get(User, comp.user_id)
        seeker = db.query(Seeker).first()
        seeker_user = db.get(User, seeker.user_id)
        app_row = (
            db.query(Application)
            .join(Job)
            .filter(Job.company_id == comp.id)
            .first()
        )
        job_id = job.id
        job_slug = job.slug
        comp_slug = comp.slug
        comp_email = comp_user.email
        seeker_email = seeker_user.email
        app_id = app_row.id if app_row else None
    finally:
        db.close()

    print("\n── Halaman publik ────────────────────────────────────────────")
    with TestClient(app) as c:
        for u in ["/health", "/", "/lowongan", "/lowongan?q=operator", "/perusahaan-mitra", "/tentang",
                  "/masuk", "/daftar", "/daftar/pencari-kerja", "/daftar/perusahaan",
                  f"/lowongan/{job_slug}", f"/perusahaan-mitra/{comp_slug}"]:
            get(c, u)
        get(c, "/lowongan/slug-yang-tidak-ada", 404)
        get(c, "/admin", 303)
        get(c, "/perusahaan", 303)
        get(c, "/pelamar", 303)

    print("\n── Peran admin ───────────────────────────────────────────────")
    with TestClient(app) as c:
        r = c.post("/masuk", data={"email": settings.admin_email, "password": settings.admin_password},
                   follow_redirects=False)
        cek("Login admin", r.status_code == 303, f"status {r.status_code}")
        for u in ["/admin", "/admin/perusahaan", "/admin/perusahaan?status_filter=pending", "/admin/lowongan",
                  "/admin/lowongan?status_filter=pending", "/admin/pengguna", "/admin/pengguna?role=seeker",
                  "/admin/lamaran", "/admin/laporan", "/admin/pengumuman", "/admin/log",
                  "/admin/laporan/ekspor?jenis=lamaran", "/admin/laporan/ekspor?jenis=lowongan",
                  "/admin/laporan/ekspor?jenis=perusahaan",
                  "/admin/jurusan", "/admin/laporan?lulus=2025",
                  "/admin/laporan/ekspor?jenis=serapan"]:
            get(c, u)
        r = c.get("/admin/laporan/ekspor?jenis=lamaran")
        cek("Ekspor CSV berisi header", r.text.startswith("ID,"), r.text[:40])

        # ── Jurusan & laporan serapan ──────────────────────────────────────
        r = c.get("/admin/laporan/ekspor?jenis=serapan")
        cek("Ekspor serapan berisi kolom jurusan",
            r.text.startswith("Kode,Kompetensi Keahlian,"), r.text[:60])

        r = c.get("/admin/laporan")
        cek("Laporan menampilkan serapan per jurusan",
            "Serapan kerja per kompetensi keahlian" in r.text)

        db = SessionLocal()
        try:
            jumlah_awal = db.query(Major).count()
        finally:
            db.close()

        r = c.post("/admin/jurusan", data={
            "code": "UJI", "name": "Jurusan Uji Asap", "sort_order": "99", "is_active": "1",
        }, follow_redirects=False)
        cek("Tambah jurusan", r.status_code == 303, f"status {r.status_code}")

        db = SessionLocal()
        try:
            baru = db.query(Major).filter(Major.code == "UJI").first()
            cek("Jurusan baru tersimpan dengan slug", bool(baru and baru.slug == "jurusan-uji-asap"),
                getattr(baru, "slug", None))
            cek("Jumlah jurusan bertambah", db.query(Major).count() == jumlah_awal + 1)
            uji_id = baru.id if baru else 0
        finally:
            db.close()

        r = c.post("/admin/jurusan", data={
            "code": "UJI", "name": "Nama Lain", "sort_order": "0", "is_active": "1",
        }, follow_redirects=True)
        cek("Tolak kode jurusan ganda", "sudah dipakai" in r.text)

        if uji_id:
            r = c.post(f"/admin/jurusan/{uji_id}/aktif", follow_redirects=False)
            cek("Nonaktifkan jurusan", r.status_code == 303, f"status {r.status_code}")
            r = c.post(f"/admin/jurusan/{uji_id}/hapus", follow_redirects=False)
            cek("Hapus jurusan tak terpakai", r.status_code == 303, f"status {r.status_code}")

        # Jurusan yang sudah dipakai tidak boleh terhapus.
        db = SessionLocal()
        try:
            terpakai = (
                db.query(Major).join(Seeker, Seeker.major_id == Major.id).first()
            )
            terpakai_id = terpakai.id if terpakai else 0
        finally:
            db.close()
        if terpakai_id:
            r = c.post(f"/admin/jurusan/{terpakai_id}/hapus", follow_redirects=True)
            cek("Tolak hapus jurusan yang masih dipakai", "tidak dapat dihapus" in r.text)
            db = SessionLocal()
            try:
                cek("Jurusan terpakai masih ada", db.get(Major, terpakai_id) is not None)
            finally:
                db.close()

    print("\n── Peran perusahaan ──────────────────────────────────────────")
    with TestClient(app) as c:
        r = c.post("/masuk", data={"email": comp_email, "password": "Perusahaan#123"}, follow_redirects=False)
        cek("Login perusahaan", r.status_code == 303, f"status {r.status_code}")
        for u in ["/perusahaan", "/perusahaan/lowongan", "/perusahaan/lowongan/baru",
                  "/perusahaan/pelamar", "/perusahaan/profil", f"/perusahaan/lowongan/{job_id}/ubah"]:
            get(c, u)
        if app_id:
            get(c, f"/perusahaan/pelamar/{app_id}")
        r = c.post("/perusahaan/lowongan/simpan", data={
            "title": "Uji Asap Lowongan", "description": "Deskripsi uji asap.", "location": "Pati",
            "employment_type": "full_time", "quota": "1", "aksi": "draft",
            "min_education": "SMK/SMA Sederajat", "gender_pref": "Semua",
        }, follow_redirects=False)
        cek("Buat lowongan draf", r.status_code == 303, f"status {r.status_code}")
        get(c, "/admin", 403)

    print("\n── Peran pencari kerja ───────────────────────────────────────")
    with TestClient(app) as c:
        r = c.post("/masuk", data={"email": seeker_email, "password": "Pelamar#123"}, follow_redirects=False)
        cek("Login pencari kerja", r.status_code == 303, f"status {r.status_code}")
        for u in ["/pelamar", "/pelamar/lamaran", "/pelamar/tersimpan", "/pelamar/profil", "/akun/kata-sandi"]:
            get(c, u)
        r = c.post(f"/pelamar/simpan/{job_id}", data={"kembali": "/pelamar/tersimpan"}, follow_redirects=False)
        cek("Simpan lowongan", r.status_code == 303, f"status {r.status_code}")
        get(c, "/perusahaan/lowongan", 403)

    print("\n── Validasi formulir ─────────────────────────────────────────")
    with TestClient(app) as c:
        r = c.post("/masuk", data={"email": settings.admin_email, "password": "salah"})
        cek("Tolak kata sandi salah", r.status_code == 401, f"status {r.status_code}")
        r = c.post("/daftar/pencari-kerja", data={
            "full_name": "Uji", "email": "uji.asap@contoh.id", "password": "abc",
            "password_confirm": "abc", "agree": "1",
        })
        cek("Tolak kata sandi lemah", r.status_code == 400 and "minimal 8 karakter" in r.text)

    # ── Formulir benar-benar tersambung ke router ─────────────────────────
    #
    # Pengujian di bawah mengirim data memakai nama field yang dibaca dari HTML
    # yang benar-benar dirender, bukan nama yang diasumsikan. Tanpa ini, salah
    # ketik nama field lolos tanpa terdeteksi: formulir tampak normal, tetapi
    # nilainya diam-diam tidak tersimpan.
    print("\n── Formulir tersambung ke router ─────────────────────────────")
    with TestClient(app) as c:
        db = SessionLocal()
        try:
            jurusan = db.query(Major).order_by(Major.sort_order).first()
            jid = jurusan.id
            jnama = jurusan.name
        finally:
            db.close()

        html = c.get("/daftar/pencari-kerja").text
        field = set(re.findall(r'name="([a-zA-Z_]+)"', html))
        for wajib in ("full_name", "email", "major_id", "class_name", "interest", "graduation_year"):
            cek(f"Formulir daftar punya field '{wajib}'", wajib in field,
                f"field tersedia: {sorted(field)}")

        email_uji = "uji.formulir@contoh.id"
        c.post("/daftar/pencari-kerja", data={
            "full_name": "Uji Formulir", "email": email_uji, "phone": "081200000000",
            "nis": "20260001", "class_name": "XII TKJ 1", "major_id": str(jid),
            "graduation_year": "2026", "interest": "kerja",
            "password": "Rahasia123", "password_confirm": "Rahasia123", "agree": "1",
        }, follow_redirects=False)

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email_uji).first()
            sk = db.query(Seeker).filter(Seeker.user_id == u.id).first() if u else None
            cek("Pendaftaran menyimpan jurusan", bool(sk and sk.major_id == jid),
                f"major_id={getattr(sk, 'major_id', None)} (harusnya {jid} = {jnama})")
            cek("Pendaftaran menyimpan kelas", bool(sk and sk.class_name == "XII TKJ 1"),
                f"class_name={getattr(sk, 'class_name', None)}")
            cek("Pendaftaran menyimpan minat", bool(sk and sk.interest == Interest.KERJA),
                f"interest={getattr(sk, 'interest', None)}")
        finally:
            db.close()

        # Profil: bandingkan field yang dirender dengan yang benar-benar tersimpan.
        c.post("/masuk", data={"email": email_uji, "password": "Rahasia123"}, follow_redirects=True)
        html = c.get("/pelamar/profil").text
        field = set(re.findall(r'name="([a-zA-Z_]+)"', html))
        for wajib in ("major_id", "class_name", "religion", "education_level",
                      "interest", "social_media", "address", "gender"):
            cek(f"Formulir profil punya field '{wajib}'", wajib in field)

        c.post("/pelamar/profil", data={
            "full_name": "Uji Formulir", "nis": "20260001", "class_name": "XII RPL 2",
            "phone": "081200000001", "gender": "P", "religion": "Katolik",
            "birth_place": "Pati", "birth_date": "2007-01-15", "city": "Pati",
            "address": "Jalan Uji Nomor 1", "social_media": "tiktok.com/@ujiformulir",
            "major_id": str(jid), "graduation_year": "2026",
            "education_level": "SMK/SMA Sederajat", "interest": "kuliah",
            "headline": "Uji", "summary": "-", "skills": "Uji",
            "experience": "", "education": "", "open_to_work": "1",
        }, follow_redirects=False)

        db = SessionLocal()
        try:
            sk = db.query(Seeker).join(User).filter(User.email == email_uji).first()
            tersimpan = {
                "kelas": sk.class_name == "XII RPL 2",
                "agama": sk.religion == "Katolik",
                "pendidikan": sk.education_level == "SMK/SMA Sederajat",
                "minat": sk.interest == Interest.KULIAH,
                "medsos": sk.social_media == "tiktok.com/@ujiformulir",
                "alamat": sk.address == "Jalan Uji Nomor 1",
                "jenis kelamin": sk.gender == "P",
                "jurusan": sk.major_id == jid,
            }
            for nama_field, ok_ in tersimpan.items():
                cek(f"Profil menyimpan {nama_field}", ok_)
        finally:
            db.close()

        # Ekspor data siswa memuat kolom yang diminta sekolah.
        c.post("/keluar")
        c.post("/masuk", data={"email": settings.admin_email, "password": settings.admin_password},
               follow_redirects=True)
        r = c.get("/admin/laporan/ekspor?jenis=siswa")
        judul = r.text.splitlines()[0] if r.text else ""
        cek("Ekspor data siswa memuat 12 kolom yang diminta",
            judul == "Tahun Lulus,Nama,Kelas,Jurusan,Minat,Jenis Kelamin,Agama,"
                     "Pendidikan,No HP,Email,Alamat,Alamat Medsos", judul)
        cek("Ekspor data siswa berisi baris data", len(r.text.strip().splitlines()) > 1)

        # Bersihkan akun uji.
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email_uji).first()
            if u:
                db.delete(u)
                db.commit()
        finally:
            db.close()

    print(f"\n{'='*62}\nBerhasil: {len(OK)}   Gagal: {len(GAGAL)}")
    if GAGAL:
        print("Rute bermasalah: " + ", ".join(GAGAL))
    return 1 if GAGAL else 0


if __name__ == "__main__":
    raise SystemExit(main())
