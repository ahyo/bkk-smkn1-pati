"""Dashboard perusahaan: profil, kelola lowongan, seleksi pelamar."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import company_required, current_company, redirect
from app.models import (
    Application,
    ApplicationStatus,
    Company,
    EmploymentType,
    Job,
    JobStatus,
    Seeker,
    User,
)
from app.routers.auth import log_activity
from app.templating import render
from app.utils import ALLOWED_IMG, daftar_jurusan, flash, paginate, save_upload, unique_slug

router = APIRouter(prefix="/perusahaan", tags=["perusahaan"], dependencies=[Depends(company_required)])


def _parse_decimal(raw: str) -> float | None:
    raw = (raw or "").replace(".", "").replace(",", "").strip()
    return float(raw) if raw.isdigit() else None


@router.get("")
@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db), company: Company = Depends(current_company)):
    job_ids = [r[0] for r in db.query(Job.id).filter(Job.company_id == company.id).all()]

    by_job_status = dict(
        db.query(Job.status, func.count(Job.id)).filter(Job.company_id == company.id).group_by(Job.status).all()
    )
    by_app_status = dict(
        db.query(Application.status, func.count(Application.id))
        .filter(Application.job_id.in_(job_ids or [0]))
        .group_by(Application.status)
        .all()
    )

    stats = {
        "tayang": by_job_status.get(JobStatus.PUBLISHED, 0),
        "menunggu": by_job_status.get(JobStatus.PENDING, 0),
        "draf": by_job_status.get(JobStatus.DRAFT, 0),
        "pelamar": sum(by_app_status.values()),
        "baru": by_app_status.get(ApplicationStatus.SUBMITTED, 0),
        "diterima": by_app_status.get(ApplicationStatus.ACCEPTED, 0),
        "views": db.query(func.coalesce(func.sum(Job.views), 0)).filter(Job.company_id == company.id).scalar(),
    }

    pelamar_terbaru = (
        db.query(Application)
        .options(joinedload(Application.seeker).joinedload(Seeker.user), joinedload(Application.job))
        .filter(Application.job_id.in_(job_ids or [0]))
        .order_by(Application.created_at.desc())
        .limit(6)
        .all()
    )

    lowongan_aktif = (
        db.query(Job)
        .filter(Job.company_id == company.id, Job.status == JobStatus.PUBLISHED)
        .order_by(Job.published_at.desc().nullslast())
        .limit(5)
        .all()
    )
    counts = dict(
        db.query(Application.job_id, func.count(Application.id))
        .filter(Application.job_id.in_(job_ids or [0]))
        .group_by(Application.job_id)
        .all()
    )

    return render(
        request,
        "company/dashboard.html",
        {
            "company": company,
            "stats": stats,
            "pelamar_terbaru": pelamar_terbaru,
            "lowongan_aktif": lowongan_aktif,
            "counts": counts,
            "by_app_status": by_app_status,
        },
    )


# ── Profil perusahaan ───────────────────────────────────────────────────────

@router.get("/profil")
async def profil(request: Request, db: Session = Depends(get_db), user: User = Depends(company_required)):
    company = db.query(Company).filter(Company.user_id == user.id).first()
    if not company:
        company = Company(user_id=user.id, name=user.full_name, slug=unique_slug(db, Company, user.full_name))
        db.add(company)
        db.commit()
        db.refresh(company)
    return render(request, "company/profile.html", {"company": company})


@router.post("/profil")
async def simpan_profil(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(company_required),
    company: Company = Depends(current_company),
    name: str = Form(...),
    industry: str = Form(""),
    city: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    website: str = Form(""),
    contact_person: str = Form(""),
    employee_count: str = Form(""),
    description: str = Form(""),
    logo: UploadFile | None = File(None),
):
    if name.strip() != company.name:
        company.slug = unique_slug(db, Company, name)
    company.name = name.strip()
    company.industry = industry.strip() or None
    company.city = city.strip() or None
    company.address = address.strip() or None
    company.phone = phone.strip() or None
    company.website = website.strip() or None
    company.contact_person = contact_person.strip() or None
    company.employee_count = employee_count.strip() or None
    company.description = description.strip() or None
    if contact_person.strip():
        user.full_name = contact_person.strip()

    if (path := save_upload(logo, "logo", ALLOWED_IMG)):
        company.logo = path

    log_activity(db, user, "update_company", f"Profil {company.name} diperbarui")
    db.commit()
    flash(request, "Profil perusahaan berhasil disimpan.", "success")
    return redirect("/perusahaan/profil")


# ── Kelola lowongan ─────────────────────────────────────────────────────────

@router.get("/lowongan")
async def daftar_lowongan(
    request: Request,
    db: Session = Depends(get_db),
    company: Company = Depends(current_company),
    status_filter: str = "",
    q: str = "",
    page: int = 1,
):
    query = db.query(Job).filter(Job.company_id == company.id)
    if status_filter:
        try:
            query = query.filter(Job.status == JobStatus(status_filter))
        except ValueError:
            pass
    if q:
        query = query.filter(Job.title.ilike(f"%{q.strip()}%"))
    query = query.order_by(Job.created_at.desc())
    jobs, meta = paginate(query, page, per_page=10)

    counts = dict(
        db.query(Application.job_id, func.count(Application.id))
        .filter(Application.job_id.in_([j.id for j in jobs] or [0]))
        .group_by(Application.job_id)
        .all()
    )
    return render(
        request,
        "company/jobs.html",
        {"jobs": jobs, "meta": meta, "counts": counts, "status_filter": status_filter, "q": q, "company": company},
    )


@router.get("/lowongan/baru")
async def form_lowongan_baru(
    request: Request, db: Session = Depends(get_db), company: Company = Depends(current_company)
):
    if settings.require_company_verification and not company.is_verified:
        flash(request, "Akun perusahaan Anda belum terverifikasi admin BKK.", "warning")
        return redirect("/perusahaan")
    return render(
        request, "company/job_form.html",
        {"job": None, "company": company, "majors": daftar_jurusan(db)},
    )


@router.get("/lowongan/{job_id}/ubah")
async def form_lowongan_ubah(
    job_id: int, request: Request, db: Session = Depends(get_db), company: Company = Depends(current_company)
):
    job = db.get(Job, job_id)
    if not job or job.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")
    return render(
        request, "company/job_form.html",
        {"job": job, "company": company, "majors": daftar_jurusan(db)},
    )


@router.post("/lowongan/simpan")
async def simpan_lowongan(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(company_required),
    company: Company = Depends(current_company),
    job_id: str = Form(""),
    title: str = Form(...),
    description: str = Form(...),
    requirements: str = Form(""),
    benefits: str = Form(""),
    major_id: str = Form(""),
    employment_type: str = Form("full_time"),
    location: str = Form(...),
    is_remote: str = Form(""),
    salary_min: str = Form(""),
    salary_max: str = Form(""),
    salary_hidden: str = Form(""),
    quota: str = Form("1"),
    min_education: str = Form("SMK/SMA Sederajat"),
    max_age: str = Form(""),
    gender_pref: str = Form("Semua"),
    deadline: str = Form(""),
    aksi: str = Form("submit"),   # "draft" | "submit"
):
    if settings.require_company_verification and not company.is_verified:
        flash(request, "Perusahaan belum terverifikasi. Lowongan tidak dapat dipublikasikan.", "danger")
        return redirect("/perusahaan")

    if job_id.isdigit():
        job = db.get(Job, int(job_id))
        if not job or job.company_id != company.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")
        if job.title != title.strip():
            job.slug = unique_slug(db, Job, f"{title}-{company.name}")
    else:
        job = Job(company_id=company.id, slug=unique_slug(db, Job, f"{title}-{company.name}"))
        db.add(job)

    job.title = title.strip()
    job.description = description.strip()
    job.requirements = requirements.strip() or None
    job.benefits = benefits.strip() or None
    job.major_id = int(major_id) if major_id.isdigit() else None
    try:
        job.employment_type = EmploymentType(employment_type)
    except ValueError:
        job.employment_type = EmploymentType.FULL_TIME
    job.location = location.strip()
    job.is_remote = bool(is_remote)
    job.salary_min = _parse_decimal(salary_min)
    job.salary_max = _parse_decimal(salary_max)
    job.salary_hidden = bool(salary_hidden)
    job.quota = int(quota) if quota.isdigit() else 1
    job.min_education = min_education.strip() or None
    job.max_age = int(max_age) if max_age.isdigit() else None
    job.gender_pref = gender_pref or "Semua"
    job.deadline = date.fromisoformat(deadline) if deadline else None

    if aksi == "draft":
        job.status = JobStatus.DRAFT
        pesan = "Lowongan disimpan sebagai draf."
    elif settings.require_job_approval:
        job.status = JobStatus.PENDING
        pesan = "Lowongan dikirim dan menunggu persetujuan admin BKK."
    else:
        job.status = JobStatus.PUBLISHED
        job.published_at = job.published_at or datetime.now()
        pesan = "Lowongan berhasil ditayangkan."

    log_activity(db, user, "save_job", f"{company.name} menyimpan lowongan '{job.title}' ({job.status.value})")
    db.commit()
    flash(request, pesan, "success")
    return redirect("/perusahaan/lowongan")


@router.post("/lowongan/{job_id}/tutup")
async def tutup_lowongan(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(company_required),
    company: Company = Depends(current_company),
):
    job = db.get(Job, job_id)
    if not job or job.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")
    job.status = JobStatus.CLOSED
    log_activity(db, user, "close_job", f"Menutup lowongan '{job.title}'")
    db.commit()
    flash(request, "Lowongan ditutup.", "info")
    return redirect("/perusahaan/lowongan")


@router.post("/lowongan/{job_id}/hapus")
async def hapus_lowongan(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(company_required),
    company: Company = Depends(current_company),
):
    job = db.get(Job, job_id)
    if not job or job.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")
    if db.query(Application).filter(Application.job_id == job.id).count():
        flash(request, "Lowongan yang sudah memiliki pelamar tidak dapat dihapus — tutup saja.", "warning")
        return redirect("/perusahaan/lowongan")
    judul = job.title
    db.delete(job)
    log_activity(db, user, "delete_job", f"Menghapus lowongan '{judul}'")
    db.commit()
    flash(request, "Lowongan dihapus.", "info")
    return redirect("/perusahaan/lowongan")


# ── Seleksi pelamar ─────────────────────────────────────────────────────────

@router.get("/pelamar")
async def daftar_pelamar(
    request: Request,
    db: Session = Depends(get_db),
    company: Company = Depends(current_company),
    job_id: str = "",
    status_filter: str = "",
    q: str = "",
    page: int = 1,
):
    job_ids = [r[0] for r in db.query(Job.id).filter(Job.company_id == company.id).all()]
    query = (
        db.query(Application)
        .join(Seeker)
        .join(User, Seeker.user_id == User.id)
        .options(
            joinedload(Application.seeker).joinedload(Seeker.user),
            joinedload(Application.job),
        )
        .filter(Application.job_id.in_(job_ids or [0]))
    )
    if job_id.isdigit():
        query = query.filter(Application.job_id == int(job_id))
    if status_filter:
        try:
            query = query.filter(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.full_name.ilike(like), Seeker.skills.ilike(like)))

    query = query.order_by(Application.created_at.desc())
    apps, meta = paginate(query, page, per_page=12)

    jobs = db.query(Job).filter(Job.company_id == company.id).order_by(Job.title).all()
    return render(
        request,
        "company/applicants.html",
        {
            "apps": apps,
            "meta": meta,
            "jobs": jobs,
            "job_id": job_id,
            "status_filter": status_filter,
            "q": q,
        },
    )


@router.get("/pelamar/{app_id}")
async def detail_pelamar(
    app_id: int, request: Request, db: Session = Depends(get_db), company: Company = Depends(current_company)
):
    app_obj = (
        db.query(Application)
        .options(joinedload(Application.seeker).joinedload(Seeker.user), joinedload(Application.job))
        .filter(Application.id == app_id)
        .first()
    )
    if not app_obj or app_obj.job.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Data pelamar tidak ditemukan.")

    riwayat = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.seeker_id == app_obj.seeker_id, Application.id != app_obj.id)
        .order_by(Application.created_at.desc())
        .limit(5)
        .all()
    )
    return render(request, "company/applicant_detail.html", {"app": app_obj, "riwayat": riwayat})


@router.post("/pelamar/{app_id}/status")
async def ubah_status_pelamar(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(company_required),
    company: Company = Depends(current_company),
    new_status: str = Form(...),
    company_note: str = Form(""),
    interview_at: str = Form(""),
):
    app_obj = db.get(Application, app_id)
    if not app_obj or app_obj.job.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Data pelamar tidak ditemukan.")

    try:
        app_obj.status = ApplicationStatus(new_status)
    except ValueError:
        flash(request, "Status tidak dikenal.", "danger")
        return redirect(f"/perusahaan/pelamar/{app_id}")

    app_obj.company_note = company_note.strip() or None
    app_obj.interview_at = datetime.fromisoformat(interview_at) if interview_at else None

    log_activity(
        db, user, "update_application",
        f"Status lamaran #{app_obj.id} → {app_obj.status.value}",
    )
    db.commit()
    flash(request, "Status pelamar diperbarui.", "success")
    return redirect(f"/perusahaan/pelamar/{app_id}")
