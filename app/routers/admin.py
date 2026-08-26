"""Dashboard admin BKK: pemantauan pengguna, verifikasi perusahaan,
moderasi lowongan, rekap lamaran, pengumuman, dan log aktivitas."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, or_
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
    JobStatus,
    Role,
    Seeker,
    User,
)
from app.routers.auth import log_activity
from app.security import hash_password, password_issues
from app.templating import render
from app.utils import flash, paginate, tanggal

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_required)])


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
    tren = [{"label": tanggal(r[0])[-8:] if r[0] else "-", "value": r[1]} for r in rows]
    tren_max = max([t["value"] for t in tren], default=1) or 1

    per_jurusan = (
        db.query(Job.major_target, func.count(Job.id))
        .filter(Job.status == JobStatus.PUBLISHED)
        .group_by(Job.major_target)
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
            "per_jurusan": [(m or "Umum", c) for m, c in per_jurusan],
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
async def laporan(request: Request, db: Session = Depends(get_db), tahun: str = ""):
    tahun_int = int(tahun) if tahun.isdigit() else date.today().year

    per_jurusan = (
        db.query(
            Seeker.major,
            func.count(func.distinct(Seeker.id)).label("pelamar"),
            func.count(Application.id).label("lamaran"),
            func.coalesce(
                func.sum(case((Application.status == ApplicationStatus.ACCEPTED, 1), else_=0)), 0
            ).label("diterima"),
        )
        .outerjoin(Application, Application.seeker_id == Seeker.id)
        .group_by(Seeker.major)
        .order_by(func.count(Application.id).desc())
        .all()
    )

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
            "per_perusahaan": per_perusahaan,
            "bulan_map": bulan_map,
            "bulan_max": max(bulan_map.values(), default=1) or 1,
            "tahun": tahun_int,
            "tahun_tersedia": tahun_tersedia,
        },
    )


@router.get("/laporan/ekspor")
async def ekspor_csv(db: Session = Depends(get_db), jenis: str = "lamaran"):
    buf = io.StringIO()
    writer = csv.writer(buf)

    if jenis == "lowongan":
        writer.writerow(["ID", "Judul", "Perusahaan", "Lokasi", "Jurusan", "Status", "Kuota", "Deadline", "Dibuat"])
        for j in db.query(Job).options(joinedload(Job.company)).order_by(Job.id).all():
            writer.writerow([
                j.id, j.title, j.company.name if j.company else "-", j.location,
                j.major_target or "-", j.status.value, j.quota,
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
                joinedload(Application.job).joinedload(Job.company),
            )
            .order_by(Application.id)
        )
        for a in q.all():
            writer.writerow([
                a.id, a.seeker.user.full_name, a.seeker.nis or "-", a.seeker.major or "-",
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
