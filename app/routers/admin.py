"""Dashboard admin BKK: pemantauan pengguna, verifikasi perusahaan,
moderasi lowongan, rekap lamaran, pengumuman, dan log aktivitas."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import admin_required, redirect
from app.models import (
    ActivityLog,
    Announcement,
    Application,
    ApplicationStatus,
    Company,
    CompanyStatus,
    Job,
    INTEREST_LABEL,
    Interest,
    JobStatus,
    Major,
    Role,
    Seeker,
    User,
)
from app.routers.auth import log_activity
from app.security import hash_password, password_issues
from app.templating import render
from app.utils import bulan_tahun, flash, paginate, slugify

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_required)])


def serapan_per_jurusan(db: Session, tahun_lulus: int | None = None) -> list[dict]:
    """Rekap serapan kerja per kompetensi keahlian.

    "Terserap" dihitung sebagai jumlah *alumni berbeda* yang punya minimal satu
    lamaran berstatus diterima — bukan jumlah lamaran diterima, karena satu
    alumnus bisa diterima di lebih dari satu perusahaan dan itu tetap satu
    orang yang terserap.

    Saringan tahun lulus sengaja diletakkan pada klausa ON, bukan WHERE, agar
    jurusan yang belum punya alumni pada tahun itu tetap muncul dengan nilai 0.
    """
    join_seeker = [Seeker.major_id == Major.id]
    if tahun_lulus:
        join_seeker.append(Seeker.graduation_year == tahun_lulus)

    rows = (
        db.query(
            Major.id.label("id"),
            Major.code.label("code"),
            Major.name.label("name"),
            Major.is_active.label("is_active"),
            func.count(func.distinct(Seeker.id)).label("alumni"),
            func.count(func.distinct(case((Application.id.isnot(None), Seeker.id)))).label("melamar"),
            func.count(Application.id).label("lamaran"),
            func.count(
                func.distinct(case((Application.status == ApplicationStatus.ACCEPTED, Seeker.id)))
            ).label("terserap"),
        )
        .select_from(Major)
        .outerjoin(Seeker, and_(*join_seeker))
        .outerjoin(Application, Application.seeker_id == Seeker.id)
        .group_by(Major.id, Major.code, Major.name, Major.is_active, Major.sort_order)
        .order_by(Major.sort_order, Major.name)
        .all()
    )

    # Lowongan tayang per jurusan dihitung terpisah supaya tidak menggandakan
    # baris pada join di atas.
    lowongan = dict(
        db.query(Job.major_id, func.count(Job.id))
        .filter(Job.status == JobStatus.PUBLISHED)
        .group_by(Job.major_id)
        .all()
    )

    hasil = []
    for r in rows:
        hasil.append({
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "is_active": r.is_active,
            "alumni": r.alumni,
            "melamar": r.melamar,
            "lamaran": r.lamaran,
            "terserap": r.terserap,
            "lowongan": lowongan.get(r.id, 0),
            "persen": round(r.terserap / r.alumni * 100, 1) if r.alumni else 0.0,
            "persen_pelamar": round(r.terserap / r.melamar * 100, 1) if r.melamar else 0.0,
        })
    return hasil


def tahun_lulus_tersedia(db: Session) -> list[int]:
    return [
        int(r[0])
        for r in db.query(Seeker.graduation_year)
        .filter(Seeker.graduation_year.isnot(None))
        .distinct()
        .order_by(Seeker.graduation_year.desc())
        .all()
    ]


@router.get("")
@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = {
        "pengguna": db.query(User).count(),
        "pelamar": db.query(Seeker).count(),
        "perusahaan": db.query(Company).count(),
        "perusahaan_verified": db.query(Company).filter(Company.status == CompanyStatus.VERIFIED).count(),
        "perusahaan_pending": db.query(Company).filter(Company.status == CompanyStatus.PENDING).count(),
        "lowongan": db.query(Job).count(),
        "lowongan_tayang": db.query(Job).filter(Job.status == JobStatus.PUBLISHED).count(),
        "lowongan_pending": db.query(Job).filter(Job.status == JobStatus.PENDING).count(),
        "lamaran": db.query(Application).count(),
        "diterima": db.query(Application).filter(Application.status == ApplicationStatus.ACCEPTED).count(),
    }
    stats["serapan"] = round(stats["diterima"] / stats["lamaran"] * 100, 1) if stats["lamaran"] else 0.0

    antrian_perusahaan = (
        db.query(Company)
        .filter(Company.status == CompanyStatus.PENDING)
        .order_by(Company.created_at.desc())
        .limit(5)
        .all()
    )
    antrian_lowongan = (
        db.query(Job)
        .options(joinedload(Job.company))
        .filter(Job.status == JobStatus.PENDING)
        .order_by(Job.created_at.desc())
        .limit(5)
        .all()
    )

    # Tren lamaran 6 bulan terakhir.
    sejak = date.today().replace(day=1) - timedelta(days=150)
    rows = (
        db.query(func.date_trunc("month", Application.created_at).label("bulan"), func.count(Application.id))
        .filter(Application.created_at >= sejak)
        .group_by("bulan")
        .order_by("bulan")
        .all()
    )
    tren = [{"label": bulan_tahun(r[0]), "value": r[1]} for r in rows]
    tren_max = max([t["value"] for t in tren], default=1) or 1

    per_jurusan = (
        db.query(Major.name, func.count(Job.id))
        .select_from(Job)
        .outerjoin(Major, Job.major_id == Major.id)
        .filter(Job.status == JobStatus.PUBLISHED)
        .group_by(Major.name)
        .order_by(func.count(Job.id).desc())
        .limit(8)
        .all()
    )

    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render(
        request,
        "admin/dashboard.html",
        {
            "stats": stats,
            "antrian_perusahaan": antrian_perusahaan,
            "antrian_lowongan": antrian_lowongan,
            "tren": tren,
            "tren_max": tren_max,
            "per_jurusan": [(m or "Semua jurusan", c) for m, c in per_jurusan],
            "logs": logs,
        },
    )


# ── Perusahaan ──────────────────────────────────────────────────────────────

@router.get("/perusahaan")
async def kelola_perusahaan(
    request: Request, db: Session = Depends(get_db), status_filter: str = "", q: str = "", page: int = 1
):
    query = db.query(Company).options(joinedload(Company.user))
    if status_filter:
        try:
            query = query.filter(Company.status == CompanyStatus(status_filter))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Company.name.ilike(like), Company.city.ilike(like), Company.industry.ilike(like)))
    query = query.order_by(Company.created_at.desc())
    companies, meta = paginate(query, page, per_page=15)

    counts = dict(db.query(Job.company_id, func.count(Job.id)).group_by(Job.company_id).all())
    return render(
        request,
        "admin/companies.html",
        {"companies": companies, "meta": meta, "status_filter": status_filter, "q": q, "counts": counts},
    )


@router.post("/perusahaan/{company_id}/status")
async def ubah_status_perusahaan(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(admin_required),
    new_status: str = Form(...),
    note: str = Form(""),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Perusahaan tidak ditemukan.")
    try:
        company.status = CompanyStatus(new_status)
    except ValueError:
        flash(request, "Status tidak dikenal.", "danger")
        return redirect("/admin/perusahaan")

    company.verification_note = note.strip() or None
    company.verified_at = datetime.now() if company.status == CompanyStatus.VERIFIED else None

    log_activity(db, user, "verify_company", f"{company.name} → {company.status.value}")
    db.commit()
    flash(request, f"Status {company.name} diperbarui menjadi {company.status.value}.", "success")
    return redirect(request.headers.get("referer", "/admin/perusahaan"))


# ── Lowongan ────────────────────────────────────────────────────────────────

@router.get("/lowongan")
async def kelola_lowongan(
    request: Request, db: Session = Depends(get_db), status_filter: str = "", q: str = "", page: int = 1
):
    query = db.query(Job).options(joinedload(Job.company))
    if status_filter:
        try:
            query = query.filter(Job.status == JobStatus(status_filter))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip()}%"
        query = query.join(Company).filter(or_(Job.title.ilike(like), Company.name.ilike(like)))
    query = query.order_by(Job.created_at.desc())
    jobs, meta = paginate(query, page, per_page=15)

    counts = dict(
        db.query(Application.job_id, func.count(Application.id))
        .filter(Application.job_id.in_([j.id for j in jobs] or [0]))
        .group_by(Application.job_id)
        .all()
    )
    return render(
        request,
        "admin/jobs.html",
        {"jobs": jobs, "meta": meta, "status_filter": status_filter, "q": q, "counts": counts},
    )


@router.post("/lowongan/{job_id}/status")
async def ubah_status_lowongan(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(admin_required),
    new_status: str = Form(...),
    note: str = Form(""),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")
    try:
        job.status = JobStatus(new_status)
    except ValueError:
        flash(request, "Status tidak dikenal.", "danger")
        return redirect("/admin/lowongan")

    job.review_note = note.strip() or None
    if job.status == JobStatus.PUBLISHED and not job.published_at:
        job.published_at = datetime.now()

    log_activity(db, user, "moderate_job", f"'{job.title}' → {job.status.value}")
    db.commit()
    flash(request, f"Lowongan '{job.title}' diperbarui.", "success")
    return redirect(request.headers.get("referer", "/admin/lowongan"))


# ── Pengguna ────────────────────────────────────────────────────────────────

@router.get("/pengguna")
async def kelola_pengguna(
    request: Request, db: Session = Depends(get_db), role: str = "", q: str = "", page: int = 1
):
    query = db.query(User).options(joinedload(User.company), joinedload(User.seeker))
    if role:
        try:
            query = query.filter(User.role == Role(role))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))
    query = query.order_by(User.created_at.desc())
    users, meta = paginate(query, page, per_page=15)
    return render(request, "admin/users.html", {"users": users, "meta": meta, "role": role, "q": q})


@router.post("/pengguna/{user_id}/aktif")
async def toggle_aktif(
    user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_required)
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan.")
    if target.id == admin.id:
        flash(request, "Anda tidak dapat menonaktifkan akun sendiri.", "warning")
        return redirect("/admin/pengguna")

    target.is_active = not target.is_active
    log_activity(db, admin, "toggle_user", f"{target.email} → {'aktif' if target.is_active else 'nonaktif'}")
    db.commit()
    flash(request, f"Akun {target.email} kini {'aktif' if target.is_active else 'nonaktif'}.", "success")
    return redirect(request.headers.get("referer", "/admin/pengguna"))


@router.post("/pengguna/{user_id}/reset-sandi")
async def reset_sandi(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    new_password: str = Form(...),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan.")
    if (errors := password_issues(new_password)):
        for e in errors:
            flash(request, e, "danger")
        return redirect("/admin/pengguna")

    target.password_hash = hash_password(new_password)
    log_activity(db, admin, "reset_password", f"Reset kata sandi {target.email}")
    db.commit()
    flash(request, f"Kata sandi {target.email} telah direset.", "success")
    return redirect("/admin/pengguna")


@router.post("/pengguna/baru")
async def tambah_admin(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        flash(request, "Email sudah digunakan.", "danger")
        return redirect("/admin/pengguna")
    if (errors := password_issues(password)):
        for e in errors:
            flash(request, e, "danger")
        return redirect("/admin/pengguna")

    db.add(User(email=email, full_name=full_name.strip(), password_hash=hash_password(password), role=Role.ADMIN))
    log_activity(db, admin, "create_admin", f"Menambah admin {email}")
    db.commit()
    flash(request, "Akun admin baru dibuat.", "success")
    return redirect("/admin/pengguna")


# ── Kompetensi keahlian (jurusan) ───────────────────────────────────────────

@router.get("/jurusan")
async def kelola_jurusan(request: Request, db: Session = Depends(get_db)):
    majors = db.query(Major).order_by(Major.sort_order, Major.name).all()

    dipakai_seeker = dict(
        db.query(Seeker.major_id, func.count(Seeker.id)).group_by(Seeker.major_id).all()
    )
    dipakai_job = dict(
        db.query(Job.major_id, func.count(Job.id)).group_by(Job.major_id).all()
    )
    return render(
        request,
        "admin/majors.html",
        {"majors": majors, "dipakai_seeker": dipakai_seeker, "dipakai_job": dipakai_job},
    )


@router.post("/jurusan")
async def simpan_jurusan(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    major_id: str = Form(""),
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    sort_order: str = Form("0"),
    is_active: str = Form(""),
):
    code = code.strip().upper()
    name = name.strip()

    bentrok_q = db.query(Major).filter(or_(Major.code == code, Major.name == name))
    if major_id.isdigit():
        bentrok_q = bentrok_q.filter(Major.id != int(major_id))
    bentrok = bentrok_q.first()
    if bentrok:
        flash(request, f"Kode atau nama jurusan sudah dipakai oleh '{bentrok.name}'.", "danger")
        return redirect("/admin/jurusan")

    if major_id.isdigit():
        major = db.get(Major, int(major_id))
        if not major:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Jurusan tidak ditemukan.")
        aksi = "update_major"
    else:
        major = Major()
        db.add(major)
        aksi = "create_major"

    major.code = code
    major.name = name
    major.slug = slugify(name)
    major.description = description.strip() or None
    major.sort_order = int(sort_order) if sort_order.lstrip("-").isdigit() else 0
    major.is_active = bool(is_active)

    log_activity(db, admin, aksi, f"Jurusan {code} — {name}")
    db.commit()
    flash(request, f"Jurusan {name} disimpan.", "success")
    return redirect("/admin/jurusan")


@router.post("/jurusan/{major_id}/aktif")
async def toggle_jurusan(
    major_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_required)
):
    major = db.get(Major, major_id)
    if not major:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Jurusan tidak ditemukan.")

    major.is_active = not major.is_active
    log_activity(db, admin, "toggle_major", f"{major.name} → {'aktif' if major.is_active else 'nonaktif'}")
    db.commit()
    flash(
        request,
        f"Jurusan {major.name} kini {'aktif' if major.is_active else 'nonaktif'}. "
        "Jurusan nonaktif tidak muncul pada formulir baru, tetapi data lamanya tetap utuh.",
        "success",
    )
    return redirect("/admin/jurusan")


@router.post("/jurusan/{major_id}/hapus")
async def hapus_jurusan(
    major_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_required)
):
    major = db.get(Major, major_id)
    if not major:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Jurusan tidak ditemukan.")

    dipakai = (
        db.query(Seeker).filter(Seeker.major_id == major.id).count()
        + db.query(Job).filter(Job.major_id == major.id).count()
    )
    if dipakai:
        flash(
            request,
            f"Jurusan {major.name} masih dipakai {dipakai} data dan tidak dapat dihapus. "
            "Nonaktifkan saja agar riwayat laporan tetap utuh.",
            "warning",
        )
        return redirect("/admin/jurusan")

    nama = major.name
    db.delete(major)
    log_activity(db, admin, "delete_major", nama)
    db.commit()
    flash(request, f"Jurusan {nama} dihapus.", "info")
    return redirect("/admin/jurusan")


# ── Lamaran & laporan ───────────────────────────────────────────────────────

@router.get("/lamaran")
async def kelola_lamaran(
    request: Request, db: Session = Depends(get_db), status_filter: str = "", q: str = "", page: int = 1
):
    query = (
        db.query(Application)
        .join(Job)
        .join(Seeker)
        .join(User, Seeker.user_id == User.id)
        .options(
            joinedload(Application.job).joinedload(Job.company),
            joinedload(Application.seeker).joinedload(Seeker.user),
        )
    )
    if status_filter:
        try:
            query = query.filter(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.full_name.ilike(like), Job.title.ilike(like)))
    query = query.order_by(Application.created_at.desc())
    apps, meta = paginate(query, page, per_page=15)
    return render(
        request, "admin/applications.html",
        {"apps": apps, "meta": meta, "status_filter": status_filter, "q": q},
    )


@router.get("/laporan")
async def laporan(
    request: Request,
    db: Session = Depends(get_db),
    tahun: str = "",
    lulus: str = "",
):
    tahun_int = int(tahun) if tahun.isdigit() else date.today().year
    tahun_lulus = int(lulus) if lulus.isdigit() else None

    per_jurusan = serapan_per_jurusan(db, tahun_lulus)
    total_serapan = {
        "alumni": sum(r["alumni"] for r in per_jurusan),
        "melamar": sum(r["melamar"] for r in per_jurusan),
        "lamaran": sum(r["lamaran"] for r in per_jurusan),
        "terserap": sum(r["terserap"] for r in per_jurusan),
    }
    total_serapan["persen"] = (
        round(total_serapan["terserap"] / total_serapan["alumni"] * 100, 1)
        if total_serapan["alumni"] else 0.0
    )
    serapan_max = max((r["alumni"] for r in per_jurusan), default=1) or 1

    # Rekap rencana lulusan (tracer study) mengikuti saringan angkatan yang sama.
    minat_q = db.query(Seeker.interest, func.count(Seeker.id))
    if tahun_lulus:
        minat_q = minat_q.filter(Seeker.graduation_year == tahun_lulus)
    minat_hitung = dict(minat_q.group_by(Seeker.interest).all())
    minat_total = sum(minat_hitung.values())
    per_minat = [
        {
            "minat": m,
            "jumlah": minat_hitung.get(m, 0),
            "persen": round(minat_hitung.get(m, 0) / minat_total * 100, 1) if minat_total else 0.0,
        }
        for m in Interest
    ]
    belum_isi = minat_hitung.get(None, 0)

    per_perusahaan = (
        db.query(Company.name, func.count(Job.id).label("lowongan"), func.count(Application.id).label("lamaran"))
        .outerjoin(Job, Job.company_id == Company.id)
        .outerjoin(Application, Application.job_id == Job.id)
        .group_by(Company.id, Company.name)
        .order_by(func.count(Application.id).desc())
        .limit(15)
        .all()
    )

    per_bulan = (
        db.query(func.extract("month", Application.created_at).label("bulan"), func.count(Application.id))
        .filter(func.extract("year", Application.created_at) == tahun_int)
        .group_by("bulan")
        .order_by("bulan")
        .all()
    )
    bulan_map = {int(b): c for b, c in per_bulan}
    tahun_tersedia = sorted(
        {int(r[0]) for r in db.query(func.extract("year", Application.created_at)).distinct().all() if r[0]},
        reverse=True,
    ) or [tahun_int]

    return render(
        request,
        "admin/reports.html",
        {
            "per_jurusan": per_jurusan,
            "total_serapan": total_serapan,
            "serapan_max": serapan_max,
            "per_minat": per_minat,
            "minat_total": minat_total,
            "minat_belum_isi": belum_isi,
            "per_perusahaan": per_perusahaan,
            "bulan_map": bulan_map,
            "bulan_max": max(bulan_map.values(), default=1) or 1,
            "tahun": tahun_int,
            "tahun_tersedia": tahun_tersedia,
            "tahun_lulus": tahun_lulus,
            "lulus_tersedia": tahun_lulus_tersedia(db),
        },
    )


@router.get("/laporan/ekspor")
async def ekspor_csv(db: Session = Depends(get_db), jenis: str = "lamaran", lulus: str = ""):
    tahun_lulus = int(lulus) if lulus.isdigit() else None
    buf = io.StringIO()
    writer = csv.writer(buf)

    if jenis == "siswa":
        writer.writerow([
            "Tahun Lulus", "Nama", "Kelas", "Jurusan", "Minat", "Jenis Kelamin",
            "Agama", "Pendidikan", "No HP", "Email", "Alamat", "Alamat Medsos",
        ])
        q = (
            db.query(Seeker)
            .join(User, Seeker.user_id == User.id)
            .options(joinedload(Seeker.user), joinedload(Seeker.major))
            .order_by(Seeker.graduation_year.desc().nullslast(), User.full_name)
        )
        for sk in q.all():
            writer.writerow([
                sk.graduation_year or "-",
                sk.user.full_name,
                sk.class_name or "-",
                sk.major.name if sk.major else "-",
                INTEREST_LABEL.get(sk.interest, "-"),
                {"L": "Laki-laki", "P": "Perempuan"}.get(sk.gender, "-"),
                sk.religion or "-",
                sk.education_level or "-",
                sk.phone or "-",
                sk.user.email,
                (sk.address or "-").replace("\n", " "),
                sk.social_media or "-",
            ])
        nama = "data-siswa"
    elif jenis == "serapan":
        writer.writerow([
            "Kode", "Kompetensi Keahlian", "Alumni Terdaftar", "Melamar",
            "Total Lamaran", "Terserap Kerja", "Serapan thd Alumni (%)",
            "Serapan thd Pelamar (%)", "Lowongan Tayang",
        ])
        for r in serapan_per_jurusan(db, tahun_lulus):
            writer.writerow([
                r["code"], r["name"], r["alumni"], r["melamar"], r["lamaran"],
                r["terserap"], r["persen"], r["persen_pelamar"], r["lowongan"],
            ])
        nama = f"serapan-jurusan{'-lulus' + str(tahun_lulus) if tahun_lulus else ''}"
    elif jenis == "lowongan":
        writer.writerow(["ID", "Judul", "Perusahaan", "Lokasi", "Jurusan", "Status", "Kuota", "Deadline", "Dibuat"])
        q = db.query(Job).options(joinedload(Job.company), joinedload(Job.major)).order_by(Job.id)
        for j in q.all():
            writer.writerow([
                j.id, j.title, j.company.name if j.company else "-", j.location,
                j.major.name if j.major else "-", j.status.value, j.quota,
                j.deadline or "-", j.created_at.date() if j.created_at else "-",
            ])
        nama = "lowongan"
    elif jenis == "perusahaan":
        writer.writerow(["ID", "Nama", "Bidang", "Kota", "Status", "Kontak", "Telepon", "Terdaftar"])
        for c in db.query(Company).order_by(Company.id).all():
            writer.writerow([
                c.id, c.name, c.industry or "-", c.city or "-", c.status.value,
                c.contact_person or "-", c.phone or "-", c.created_at.date() if c.created_at else "-",
            ])
        nama = "perusahaan"
    else:
        writer.writerow(["ID", "Pelamar", "NIS", "Jurusan", "Lulus", "Lowongan", "Perusahaan", "Status", "Tanggal"])
        q = (
            db.query(Application)
            .options(
                joinedload(Application.seeker).joinedload(Seeker.user),
                joinedload(Application.seeker).joinedload(Seeker.major),
                joinedload(Application.job).joinedload(Job.company),
            )
            .order_by(Application.id)
        )
        for a in q.all():
            writer.writerow([
                a.id, a.seeker.user.full_name, a.seeker.nis or "-",
                a.seeker.major.name if a.seeker.major else "-",
                a.seeker.graduation_year or "-", a.job.title,
                a.job.company.name if a.job.company else "-",
                a.status.value, a.created_at.date() if a.created_at else "-",
            ])
        nama = "lamaran"

    buf.seek(0)
    filename = f"bkk-{nama}-{date.today():%Y%m%d}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Pengumuman ──────────────────────────────────────────────────────────────

@router.get("/pengumuman")
async def kelola_pengumuman(request: Request, db: Session = Depends(get_db)):
    items = db.query(Announcement).order_by(Announcement.created_at.desc()).all()
    return render(request, "admin/announcements.html", {"items": items})


@router.post("/pengumuman")
async def simpan_pengumuman(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    ann_id: str = Form(""),
    title: str = Form(...),
    body: str = Form(...),
    is_published: str = Form(""),
):
    if ann_id.isdigit():
        item = db.get(Announcement, int(ann_id))
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pengumuman tidak ditemukan.")
    else:
        item = Announcement(created_by=admin.id)
        db.add(item)

    item.title = title.strip()
    item.body = body.strip()
    item.is_published = bool(is_published)
    log_activity(db, admin, "announcement", item.title)
    db.commit()
    flash(request, "Pengumuman disimpan.", "success")
    return redirect("/admin/pengumuman")


@router.post("/pengumuman/{ann_id}/hapus")
async def hapus_pengumuman(
    ann_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_required)
):
    item = db.get(Announcement, ann_id)
    if item:
        db.delete(item)
        log_activity(db, admin, "announcement_delete", item.title)
        db.commit()
    flash(request, "Pengumuman dihapus.", "info")
    return redirect("/admin/pengumuman")


# ── Log aktivitas ───────────────────────────────────────────────────────────

@router.get("/log")
async def log_aktivitas(request: Request, db: Session = Depends(get_db), aksi: str = "", page: int = 1):
    query = db.query(ActivityLog)
    if aksi:
        query = query.filter(ActivityLog.action == aksi)
    query = query.order_by(ActivityLog.created_at.desc())
    logs, meta = paginate(query, page, per_page=25)
    aksi_list = [r[0] for r in db.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()]
    return render(request, "admin/logs.html", {"logs": logs, "meta": meta, "aksi": aksi, "aksi_list": aksi_list})
