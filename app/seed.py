"""Isi database dengan data contoh untuk demo dan pengujian.

Jalankan:  python -m app.seed          (tambah data bila kosong)
           python -m app.seed --reset  (hapus seluruh tabel lalu isi ulang)
"""

from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import (
    ActivityLog,
    Announcement,
    Application,
    ApplicationStatus,
    Company,
    CompanyStatus,
    DEFAULT_MAJORS,
    AGAMA,
    EmploymentType,
    Job,
    JobStatus,
    Interest,
    Major,
    PENDIDIKAN,
    Role,
    SavedJob,
    Seeker,
    User,
)
from app.security import hash_password
from app.utils import slugify

random.seed(20260826)

PERUSAHAAN = [
    ("PT Dua Kelinci", "Industri Makanan & Minuman", "Pati", "1000+",
     "Produsen makanan ringan berbahan kacang yang berdiri sejak 1972 di Pati, Jawa Tengah, "
     "dengan jaringan distribusi nasional dan ekspor."),
    ("PT Nojorono Tobacco International", "Industri Pengolahan", "Kudus", "500-1000",
     "Perusahaan pengolahan tembakau dengan standar mutu tinggi dan program pengembangan karyawan berjenjang."),
    ("CV Karya Teknologi Nusantara", "Teknologi Informasi", "Semarang", "50-200",
     "Software house yang mengerjakan sistem informasi pemerintahan, ERP, dan aplikasi mobile untuk klien nasional."),
    ("Hotel Safin Pati", "Perhotelan & Pariwisata", "Pati", "100-500",
     "Hotel bintang empat dengan fasilitas konvensi terbesar di eks-Karesidenan Pati."),
    ("PT Sukun Wartono Indonesia", "Manufaktur", "Kudus", "1000+",
     "Perusahaan manufaktur dengan lini produksi modern dan jenjang karier terbuka bagi lulusan SMK."),
    ("Bank Jateng Cabang Pati", "Perbankan & Keuangan", "Pati", "50-200",
     "Bank pembangunan daerah yang melayani perbankan ritel, kredit UMKM, dan layanan keuangan pemerintah daerah."),
    ("PT Global Retail Sejahtera", "Retail & Distribusi", "Semarang", "500-1000",
     "Jaringan retail modern dengan lebih dari 120 gerai di Jawa Tengah dan DIY."),
    ("Digital Kreatif Studio", "Agensi Kreatif & Media", "Yogyakarta", "10-50",
     "Studio kreatif yang menangani produksi konten, desain grafis, dan kampanye digital untuk merek nasional."),
]

LOWONGAN = [
    ("Operator Produksi", "PT Dua Kelinci", "Pati", "Lainnya", EmploymentType.FULL_TIME, 2500000, 3100000, 25,
     "Menjalankan mesin produksi sesuai standar operasional prosedur, melakukan pemeriksaan mutu awal, "
     "serta menjaga kebersihan dan keselamatan area kerja.",
     "- Lulusan SMK semua jurusan\n- Usia maksimal 25 tahun\n- Bersedia bekerja sistem tiga shift\n- Sehat jasmani dan tidak buta warna",
     "- Gaji sesuai UMK + tunjangan shift\n- BPJS Kesehatan & Ketenagakerjaan\n- Makan siang dan seragam kerja\n- Bus antar-jemput karyawan"),
    ("Staf Administrasi Gudang", "PT Dua Kelinci", "Pati", "Manajemen Perkantoran dan Layanan Bisnis",
     EmploymentType.CONTRACT, 2600000, 3000000, 4,
     "Mencatat keluar-masuk barang, menyusun laporan stok harian, dan mengarsipkan dokumen pengiriman.",
     "- Lulusan SMK jurusan MPLB/OTKP atau Akuntansi\n- Menguasai Microsoft Excel\n- Teliti dan terbiasa bekerja dengan angka",
     "- Kontrak 1 tahun dengan peluang diangkat tetap\n- Tunjangan kehadiran\n- Pelatihan sistem gudang"),
    ("Junior Web Developer", "CV Karya Teknologi Nusantara", "Semarang", "Rekayasa Perangkat Lunak",
     EmploymentType.FULL_TIME, 4000000, 6500000, 3,
     "Mengembangkan dan memelihara aplikasi web internal maupun klien menggunakan PHP/Laravel dan JavaScript, "
     "berkolaborasi dengan tim desain dan QA dalam siklus sprint dua mingguan.",
     "- Lulusan SMK RPL atau setara\n- Memahami HTML, CSS, JavaScript, dan salah satu framework backend\n"
     "- Terbiasa menggunakan Git\n- Memiliki portofolio proyek (tugas akhir diperbolehkan)",
     "- Gaji kompetitif + bonus proyek\n- Kerja hybrid tiga hari di kantor\n- Perangkat kerja disediakan\n- Anggaran pelatihan tahunan"),
    ("Teknisi Jaringan & Helpdesk", "CV Karya Teknologi Nusantara", "Semarang", "Teknik Komputer dan Jaringan",
     EmploymentType.FULL_TIME, 3500000, 4800000, 2,
     "Melakukan instalasi dan pemeliharaan perangkat jaringan klien, menangani tiket dukungan teknis, "
     "serta menyusun dokumentasi topologi.",
     "- Lulusan SMK TKJ\n- Memahami konfigurasi routing, switching, dan MikroTik\n- Bersedia melakukan kunjungan ke lokasi klien\n- Memiliki SIM C",
     "- Tunjangan transportasi dan pulsa\n- Sertifikasi MikroTik dibiayai perusahaan\n- BPJS lengkap"),
    ("Front Office / Receptionist", "Hotel Safin Pati", "Pati", "Perhotelan",
     EmploymentType.FULL_TIME, 2600000, 3200000, 4,
     "Melayani proses check-in dan check-out tamu, menangani reservasi, serta memberikan informasi layanan hotel "
     "dengan standar keramahan bintang empat.",
     "- Lulusan SMK Perhotelan\n- Penampilan menarik dan komunikatif\n- Mampu berbahasa Inggris dasar\n- Bersedia bekerja shift termasuk akhir pekan",
     "- Service charge bulanan\n- Makan karyawan\n- Seragam dan pelatihan hospitality"),
    ("Commis / Cook Helper", "Hotel Safin Pati", "Pati", "Kuliner",
     EmploymentType.INTERNSHIP, 1200000, 1500000, 6,
     "Membantu persiapan bahan (mise en place), menjaga kebersihan dapur, dan mendukung chef dalam pelayanan "
     "sarapan serta acara banquet.",
     "- Siswa/lulusan SMK Kuliner\n- Bersedia mengikuti program magang enam bulan\n- Disiplin terhadap standar higienitas",
     "- Uang saku dan makan\n- Sertifikat magang\n- Peluang diangkat sebagai karyawan tetap"),
    ("Teller & Customer Service", "Bank Jateng Cabang Pati", "Pati", "Akuntansi dan Keuangan Lembaga",
     EmploymentType.CONTRACT, 3200000, 4000000, 5,
     "Melayani transaksi tunai dan non-tunai nasabah, membuka rekening baru, serta menjaga akurasi kas harian.",
     "- Lulusan SMK Akuntansi/Keuangan\n- Tinggi badan minimal 155 cm (P) / 165 cm (L)\n- Teliti, jujur, dan berpenampilan rapi\n- Belum menikah diutamakan",
     "- Tunjangan jabatan dan transport\n- Program pendidikan perbankan\n- Jenjang karier ke staf tetap"),
    ("Sales Promotion Officer", "PT Global Retail Sejahtera", "Semarang", "Bisnis Daring dan Pemasaran",
     EmploymentType.FULL_TIME, 2800000, 5000000, 12,
     "Menawarkan produk kepada pelanggan di area gerai, mencapai target penjualan bulanan, dan menyusun laporan "
     "aktivitas penjualan harian.",
     "- Lulusan SMK jurusan Pemasaran/BDP\n- Komunikatif dan berorientasi target\n- Bersedia ditempatkan di seluruh gerai Jawa Tengah",
     "- Gaji pokok + komisi penjualan\n- Insentif pencapaian target\n- BPJS Ketenagakerjaan"),
    ("Desainer Grafis Junior", "Digital Kreatif Studio", "Yogyakarta", "Multimedia / Desain Komunikasi Visual",
     EmploymentType.FULL_TIME, 3500000, 5500000, 2,
     "Membuat materi visual untuk media sosial, kampanye digital, dan kebutuhan cetak klien sesuai brand guideline.",
     "- Lulusan SMK Multimedia/DKV\n- Menguasai Adobe Photoshop, Illustrator, dan dasar motion graphic\n- Wajib melampirkan portofolio",
     "- Kerja remote tiga hari per minggu\n- Bonus proyek\n- Lingkungan kerja kreatif"),
    ("Admin Media Sosial", "Digital Kreatif Studio", "Yogyakarta", "Bisnis Daring dan Pemasaran",
     EmploymentType.PART_TIME, 1800000, 2500000, 2,
     "Menjadwalkan unggahan konten, membalas interaksi pengikut, dan menyusun laporan performa mingguan.",
     "- Lulusan SMK BDP/Multimedia\n- Memahami algoritma Instagram dan TikTok\n- Mampu menulis caption yang menarik",
     "- Jam kerja fleksibel 4 jam per hari\n- Kerja penuh jarak jauh\n- Bonus performa konten"),
    ("Quality Control Inspector", "PT Sukun Wartono Indonesia", "Kudus", "Lainnya",
     EmploymentType.FULL_TIME, 2900000, 3600000, 6,
     "Memeriksa kesesuaian produk terhadap standar mutu, mendokumentasikan temuan, dan berkoordinasi dengan bagian produksi.",
     "- Lulusan SMK semua jurusan teknik\n- Teliti dan memahami dasar statistik mutu\n- Bersedia sistem shift",
     "- Tunjangan shift dan kehadiran\n- BPJS lengkap\n- Program peningkatan kompetensi"),
    ("Staf Akuntansi & Pajak", "PT Nojorono Tobacco International", "Kudus", "Akuntansi dan Keuangan Lembaga",
     EmploymentType.FULL_TIME, 3500000, 4500000, 2,
     "Melakukan pencatatan jurnal, rekonsiliasi bank, dan membantu penyusunan laporan pajak bulanan.",
     "- Lulusan SMK Akuntansi\n- Memahami dasar PPh 21 dan PPN\n- Menguasai Excel tingkat menengah\n- Teliti dan menjaga kerahasiaan data",
     "- Tunjangan makan dan transport\n- Pelatihan brevet pajak\n- Jenjang karier terstruktur"),
]

NAMA_PELAMAR = [
    ("Aditya Nugroho", "L"), ("Bella Safitri", "P"), ("Candra Wijaya", "L"), ("Dewi Anggraini", "P"),
    ("Eko Prasetyo", "L"), ("Fitria Ramadhani", "P"), ("Gilang Ramadhan", "L"), ("Hana Puspitasari", "P"),
    ("Irfan Maulana", "L"), ("Julia Rahmawati", "P"), ("Kevin Ardiansyah", "L"), ("Laila Nur Aini", "P"),
    ("Muhammad Fauzi", "L"), ("Nadia Kusuma", "P"), ("Oktavian Saputra", "L"), ("Putri Maharani", "P"),
    ("Rizky Hidayat", "L"), ("Salsabila Azzahra", "P"), ("Taufik Hidayat", "L"), ("Umi Kalsum", "P"),
]

SKILL_PER_JURUSAN = {
    "Teknik Komputer dan Jaringan": "Konfigurasi MikroTik, Instalasi LAN, Troubleshooting Hardware, Windows Server",
    "Rekayasa Perangkat Lunak": "PHP, Laravel, JavaScript, MySQL, Git, HTML/CSS",
    "Akuntansi dan Keuangan Lembaga": "Microsoft Excel, Jurnal Umum, MYOB, Perpajakan Dasar",
    "Manajemen Perkantoran dan Layanan Bisnis": "Microsoft Office, Kearsipan, Korespondensi, Administrasi Perkantoran",
    "Bisnis Daring dan Pemasaran": "Copywriting, Instagram Ads, Riset Pasar, Negosiasi",
    "Multimedia / Desain Komunikasi Visual": "Adobe Photoshop, Illustrator, Premiere Pro, Fotografi",
    "Perhotelan": "Front Office, Housekeeping, Bahasa Inggris, Table Manner",
    "Kuliner": "Pastry, Hot Kitchen, Food Plating, Higienitas Pangan",
    "Lainnya": "Kerja Tim, Kedisiplinan, Komunikasi",
}

PENGUMUMAN = [
    ("Rekrutmen Bersama PT Dua Kelinci — 12 September 2026",
     "BKK SMK Negeri 1 Pati membuka pendaftaran rekrutmen bersama PT Dua Kelinci untuk posisi Operator Produksi "
     "dan Staf Administrasi Gudang. Pendaftaran dilakukan melalui portal ini, seleksi berkas dimulai 8 September 2026. "
     "Peserta wajib membawa berkas asli saat tes tertulis di aula sekolah."),
    ("Pelatihan Pembuatan CV dan Wawancara Kerja",
     "Seluruh siswa kelas XII dan alumni diundang mengikuti pelatihan penyusunan CV serta simulasi wawancara kerja "
     "yang diselenggarakan BKK bekerja sama dengan Dinas Tenaga Kerja Kabupaten Pati. Kegiatan gratis, kuota 120 peserta."),
    ("Waspada Lowongan Kerja Palsu",
     "BKK tidak pernah memungut biaya dalam bentuk apa pun untuk penyaluran kerja. Abaikan tawaran yang meminta "
     "pembayaran administrasi, dan laporkan ke pengelola BKK bila menemukan lowongan mencurigakan yang mengatasnamakan sekolah."),
]


def reset_database() -> None:
    print("!  Menghapus seluruh tabel…")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("ℹ️  Database sudah berisi data. Gunakan --reset untuk mengisi ulang.")
            return

        # ── Admin ──────────────────────────────────────────────────────────
        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            full_name=settings.admin_name,
            role=Role.ADMIN,
        )
        db.add(admin)
        db.flush()
        print(f"  ✓ Admin: {admin.email} / {settings.admin_password}")

        # ── Kompetensi keahlian ────────────────────────────────────────────
        majors: dict[str, Major] = {}
        for urutan, (kode, nama_jurusan) in enumerate(DEFAULT_MAJORS):
            major = Major(
                code=kode,
                name=nama_jurusan,
                slug=slugify(nama_jurusan),
                sort_order=urutan,
                is_active=True,
            )
            db.add(major)
            majors[nama_jurusan] = major
        db.flush()
        print(f"  ✓ {len(majors)} kompetensi keahlian")

        # ── Perusahaan ─────────────────────────────────────────────────────
        companies: dict[str, Company] = {}
        for i, (nama, bidang, kota, karyawan, deskripsi) in enumerate(PERUSAHAAN):
            slug_email = slugify(nama).replace("-", "")[:20]
            user = User(
                email=f"hrd@{slug_email}.co.id",
                password_hash=hash_password("Perusahaan#123"),
                full_name=f"HRD {nama.split()[-1]}",
                role=Role.COMPANY,
                created_at=datetime.now() - timedelta(days=120 - i * 8),
            )
            db.add(user)
            db.flush()

            status = CompanyStatus.VERIFIED if i < 6 else CompanyStatus.PENDING
            company = Company(
                user_id=user.id,
                name=nama,
                slug=slugify(nama),
                industry=bidang,
                city=kota,
                address=f"Kawasan Industri {kota}, Jawa Tengah",
                phone=f"(029{i}) {random.randint(300000, 899999)}",
                website=f"https://www.{slug_email}.co.id",
                contact_person=user.full_name,
                employee_count=karyawan,
                description=deskripsi,
                status=status,
                verified_at=datetime.now() - timedelta(days=100 - i * 8) if status == CompanyStatus.VERIFIED else None,
                verification_note=None if status == CompanyStatus.VERIFIED else "Menunggu unggahan dokumen legalitas (NIB/akta).",
            )
            db.add(company)
            db.flush()
            companies[nama] = company
        print(f"  ✓ {len(companies)} perusahaan (6 terverifikasi, 2 menunggu verifikasi)")

        # ── Lowongan ───────────────────────────────────────────────────────
        jobs: list[Job] = []
        terbit = 0
        for i, (judul, nama_pt, lokasi, jurusan, tipe, gmin, gmax, kuota, desk, syarat, benefit) in enumerate(LOWONGAN):
            company = companies[nama_pt]
            # Lowongan dari perusahaan yang belum terverifikasi tetap masuk antrean admin.
            tayang = company.status == CompanyStatus.VERIFIED and terbit < 10
            if tayang:
                terbit += 1
            umur = 45 - i * 3
            job = Job(
                company_id=company.id,
                title=judul,
                slug=slugify(f"{judul}-{nama_pt}"),
                description=desk,
                requirements=syarat,
                benefits=benefit,
                major_id=majors[jurusan].id if jurusan else None,
                employment_type=tipe,
                location=lokasi,
                is_remote=tipe in (EmploymentType.PART_TIME,) and "Digital" in nama_pt,
                salary_min=gmin,
                salary_max=gmax,
                quota=kuota,
                min_education="SMK/SMA Sederajat",
                max_age=27 if tipe == EmploymentType.FULL_TIME else None,
                gender_pref="Semua",
                deadline=date.today() + timedelta(days=random.randint(10, 60)),
                status=JobStatus.PUBLISHED if tayang else JobStatus.PENDING,
                published_at=datetime.now() - timedelta(days=umur) if tayang else None,
                views=random.randint(20, 480) if tayang else 0,
                created_at=datetime.now() - timedelta(days=umur + 2),
            )
            db.add(job)
            db.flush()
            jobs.append(job)
        print(f"  ✓ {len(jobs)} lowongan ({terbit} tayang, {len(jobs) - terbit} menunggu persetujuan)")

        # ── Pencari kerja ──────────────────────────────────────────────────
        seekers: list[Seeker] = []
        for i, (nama, gender) in enumerate(NAMA_PELAMAR):
            jurusan = DEFAULT_MAJORS[i % (len(DEFAULT_MAJORS) - 1)][1]
            tahun_lulus = random.choice([2023, 2024, 2025, 2026])
            user = User(
                email=f"{slugify(nama).replace('-', '.')}@gmail.com",
                password_hash=hash_password("Pelamar#123"),
                full_name=nama,
                role=Role.SEEKER,
                created_at=datetime.now() - timedelta(days=random.randint(5, 200)),
            )
            db.add(user)
            db.flush()

            seeker = Seeker(
                user_id=user.id,
                nis=f"2024{1000 + i}",
                class_name=f"XII {DEFAULT_MAJORS[i % (len(DEFAULT_MAJORS) - 1)][0]} {1 + i % 3}",
                phone=f"08{random.randint(1000000000, 9999999999)}"[:13],
                gender=gender,
                birth_place=random.choice(["Pati", "Kudus", "Jepara", "Rembang", "Juwana"]),
                birth_date=date(2006 - (2026 - tahun_lulus), random.randint(1, 12), random.randint(1, 28)),
                address=f"Desa {random.choice(['Margorejo','Sukoharjo','Tambaharjo','Gembong','Winong'])}, Kabupaten Pati",
                city="Pati",
                major_id=majors[jurusan].id,
                graduation_year=tahun_lulus,
                religion=random.choices(AGAMA, weights=[70, 12, 10, 4, 3, 1])[0],
                education_level=PENDIDIKAN[0],
                interest=random.choices(
                    [Interest.KERJA, Interest.KULIAH, Interest.WIRAUSAHA, Interest.BELUM],
                    weights=[62, 24, 9, 5],
                )[0],
                social_media=f"instagram.com/{slugify(nama).replace('-', '.')}",
                headline=f"Lulusan {jurusan} — siap kerja dan cepat beradaptasi",
                summary=(
                    f"Alumni {settings.school_name} program keahlian {jurusan} tahun {tahun_lulus}. "
                    "Terbiasa bekerja dalam tim, disiplin, dan bersedia mengikuti pelatihan lanjutan."
                ),
                skills=SKILL_PER_JURUSAN.get(jurusan, "Kerja Tim, Kedisiplinan"),
                education=f"{tahun_lulus - 3}–{tahun_lulus} · {settings.school_name} — {jurusan}",
                experience=(
                    f"{tahun_lulus - 1} · Praktik Kerja Lapangan di {random.choice(list(companies))} "
                    "selama 6 bulan pada bagian yang relevan dengan jurusan."
                ),
                open_to_work=True,
            )
            db.add(seeker)
            db.flush()
            seekers.append(seeker)
        print(f"  ✓ {len(seekers)} pencari kerja")

        # ── Lamaran ────────────────────────────────────────────────────────
        published = [j for j in jobs if j.status == JobStatus.PUBLISHED]
        bobot_status = (
            [ApplicationStatus.SUBMITTED] * 5
            + [ApplicationStatus.REVIEWED] * 3
            + [ApplicationStatus.SHORTLISTED] * 2
            + [ApplicationStatus.INTERVIEW] * 2
            + [ApplicationStatus.ACCEPTED] * 2
            + [ApplicationStatus.REJECTED] * 3
        )
        jumlah = 0
        for seeker in seekers:
            cocok = [j for j in published if j.major_id == seeker.major_id] or published
            for job in random.sample(cocok, k=min(len(cocok), random.randint(1, 3))):
                if db.query(Application).filter(
                    Application.job_id == job.id, Application.seeker_id == seeker.id
                ).first():
                    continue
                status = random.choice(bobot_status)
                dibuat = datetime.now() - timedelta(days=random.randint(1, 150))
                db.add(
                    Application(
                        job_id=job.id,
                        seeker_id=seeker.id,
                        cover_letter=(
                            f"Dengan hormat, saya {seeker.user.full_name}, alumni {settings.school_name} "
                            f"program keahlian {seeker.major.name}. Saya tertarik melamar posisi {job.title} "
                            f"di {job.company.name} karena sesuai dengan kompetensi yang saya pelajari. "
                            "Besar harapan saya dapat mengikuti proses seleksi berikutnya."
                        ),
                        cv_file=None,
                        status=status,
                        company_note="Silakan hadir tepat waktu dan membawa berkas asli."
                        if status == ApplicationStatus.INTERVIEW else None,
                        interview_at=datetime.now() + timedelta(days=random.randint(2, 14))
                        if status == ApplicationStatus.INTERVIEW else None,
                        created_at=dibuat,
                        updated_at=dibuat + timedelta(days=random.randint(0, 10)),
                    )
                )
                jumlah += 1
            db.flush()

            for job in random.sample(published, k=min(len(published), random.randint(0, 2))):
                if not db.query(SavedJob).filter(
                    SavedJob.job_id == job.id, SavedJob.seeker_id == seeker.id
                ).first():
                    db.add(SavedJob(job_id=job.id, seeker_id=seeker.id))
        print(f"  ✓ {jumlah} lamaran + lowongan tersimpan")

        # ── Pengumuman & log ───────────────────────────────────────────────
        for i, (judul, isi) in enumerate(PENGUMUMAN):
            db.add(
                Announcement(
                    title=judul,
                    body=isi,
                    is_published=True,
                    created_by=admin.id,
                    created_at=datetime.now() - timedelta(days=i * 6),
                )
            )
        db.add(
            ActivityLog(
                user_id=admin.id, actor=admin.full_name, action="seed",
                detail="Data contoh dimuat untuk keperluan demo.",
            )
        )

        db.commit()
        print("\nSeed selesai. Kredensial demo:")
        print(f"   Admin      : {settings.admin_email} / {settings.admin_password}")
        print(f"   Perusahaan : {list(companies.values())[0].user.email} / Perusahaan#123")
        print(f"   Pelamar    : {seekers[0].user.email} / Pelamar#123")
    finally:
        db.close()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_database()
    seed()
