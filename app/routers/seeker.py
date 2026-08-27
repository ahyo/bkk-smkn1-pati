"""Dashboard pencari kerja: profil, lamaran, lowongan tersimpan."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import current_seeker, redirect, seeker_required
from app.models import (
    Application,
    ApplicationStatus,
    Company,
    CompanyStatus,
    Interest,
    Job,
    JobStatus,
    SavedJob,
    Seeker,
    User,
)
from app.routers.auth import log_activity
from app.templating import render
from app.utils import ALLOWED_DOC, ALLOWED_IMG, daftar_jurusan, flash, paginate, save_upload

router = APIRouter(prefix="/pelamar", tags=["pencari kerja"], dependencies=[Depends(seeker_required)])


@router.get("")
@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db), seeker: Seeker = Depends(current_seeker)):
    apps = (
        db.query(Application)
        .options(joinedload(Application.job).joinedload(Job.company))
        .filter(Application.seeker_id == seeker.id)
        .order_by(Application.created_at.desc())
        .limit(5)
        .all()
    )

    by_status = dict(
        db.query(Application.status, func.count(Application.id))
        .filter(Application.seeker_id == seeker.id)
        .group_by(Application.status)
        .all()
    )

    stats = {
        "total": sum(by_status.values()),
        "proses": sum(
            by_status.get(s, 0)
            for s in (ApplicationStatus.REVIEWED, ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW)
        ),
        "diterima": by_status.get(ApplicationStatus.ACCEPTED, 0),
        "tersimpan": db.query(SavedJob).filter(SavedJob.seeker_id == seeker.id).count(),
    }

    # Rekomendasi berdasarkan jurusan & kota.
    rec_q = (
        db.query(Job)
        .join(Company)
        .options(joinedload(Job.company))
        .filter(Job.status == JobStatus.PUBLISHED, Company.status == CompanyStatus.VERIFIED)
        .filter((Job.deadline.is_(None)) | (Job.deadline >= date.today()))
        .filter(~Job.id.in_(db.query(Application.job_id).filter(Application.seeker_id == seeker.id)))
    )
    if seeker.major_id:
        rec_q = rec_q.filter(Job.major_id == seeker.major_id)
    rekomendasi = rec_q.order_by(Job.published_at.desc().nullslast()).limit(4).all()
    if len(rekomendasi) < 4:
        extra = (
            db.query(Job)
            .join(Company)
            .options(joinedload(Job.company))
            .filter(Job.status == JobStatus.PUBLISHED, Company.status == CompanyStatus.VERIFIED)
            .filter(~Job.id.in_([j.id for j in rekomendasi]))
            .order_by(Job.published_at.desc().nullslast())
            .limit(4 - len(rekomendasi))
            .all()
        )
        rekomendasi += extra

    return render(
        request,
        "seeker/dashboard.html",
        {"seeker": seeker, "apps": apps, "stats": stats, "rekomendasi": rekomendasi, "by_status": by_status},
    )


@router.get("/profil")
async def profil(request: Request, db: Session = Depends(get_db), user: User = Depends(seeker_required)):
    seeker = db.query(Seeker).filter(Seeker.user_id == user.id).first()
    if not seeker:
        seeker = Seeker(user_id=user.id)
        db.add(seeker)
        db.commit()
        db.refresh(seeker)
    return render(request, "seeker/profile.html", {"seeker": seeker, "majors": daftar_jurusan(db)})


@router.post("/profil")
async def simpan_profil(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_required),
    seeker: Seeker = Depends(current_seeker),
    full_name: str = Form(...),
    nis: str = Form(""),
    class_name: str = Form(""),
    phone: str = Form(""),
    gender: str = Form(""),
    religion: str = Form(""),
    birth_place: str = Form(""),
    birth_date: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    major_id: str = Form(""),
    graduation_year: str = Form(""),
    education_level: str = Form(""),
    interest: str = Form(""),
    social_media: str = Form(""),
    headline: str = Form(""),
    summary: str = Form(""),
    skills: str = Form(""),
    experience: str = Form(""),
    education: str = Form(""),
    open_to_work: str = Form(""),
    photo: UploadFile | None = File(None),
    cv_file: UploadFile | None = File(None),
):
    user.full_name = full_name.strip()
    seeker.nis = nis.strip() or None
    seeker.class_name = class_name.strip() or None
    seeker.phone = phone.strip() or None
    seeker.gender = gender or None
    seeker.religion = religion or None
    seeker.birth_place = birth_place.strip() or None
    seeker.birth_date = date.fromisoformat(birth_date) if birth_date else None
    seeker.address = address.strip() or None
    seeker.city = city.strip() or None
    seeker.major_id = int(major_id) if major_id.isdigit() else None
    seeker.graduation_year = int(graduation_year) if graduation_year.isdigit() else None
    seeker.education_level = education_level or None
    seeker.interest = Interest(interest) if interest in Interest._value2member_map_ else None
    seeker.social_media = social_media.strip() or None
    seeker.headline = headline.strip() or None
    seeker.summary = summary.strip() or None
    seeker.skills = skills.strip() or None
    seeker.experience = experience.strip() or None
    seeker.education = education.strip() or None
    seeker.open_to_work = bool(open_to_work)

    if (p := save_upload(photo, "photo", ALLOWED_IMG)):
        seeker.photo = p
    if (c := save_upload(cv_file, "cv", ALLOWED_DOC)):
        seeker.cv_file = c

    log_activity(db, user, "update_profile", "Profil pencari kerja diperbarui")
    db.commit()
    flash(request, "Profil berhasil disimpan.", "success")
    return redirect("/pelamar/profil")


@router.get("/lamaran")
async def daftar_lamaran(
    request: Request,
    db: Session = Depends(get_db),
    seeker: Seeker = Depends(current_seeker),
    status_filter: str = "",
    page: int = 1,
):
    query = (
        db.query(Application)
        .options(joinedload(Application.job).joinedload(Job.company))
        .filter(Application.seeker_id == seeker.id)
    )
    if status_filter:
        try:
            query = query.filter(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass
    query = query.order_by(Application.created_at.desc())
    apps, meta = paginate(query, page, per_page=10)
    return render(
        request,
        "seeker/applications.html",
        {"apps": apps, "meta": meta, "status_filter": status_filter},
    )


@router.post("/lamar/{job_id}")
async def lamar(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_required),
    seeker: Seeker = Depends(current_seeker),
    cover_letter: str = Form(""),
    cv_file: UploadFile | None = File(None),
):
    job = db.get(Job, job_id)
    if not job or job.status != JobStatus.PUBLISHED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak tersedia.")
    if job.is_expired:
        flash(request, "Lowongan ini sudah melewati batas akhir pendaftaran.", "danger")
        return redirect(f"/lowongan/{job.slug}")

    existing = (
        db.query(Application)
        .filter(Application.job_id == job.id, Application.seeker_id == seeker.id)
        .first()
    )
    if existing:
        flash(request, "Anda sudah melamar pada lowongan ini.", "warning")
        return redirect(f"/lowongan/{job.slug}")

    uploaded = save_upload(cv_file, "cv", ALLOWED_DOC)
    cv = uploaded or seeker.cv_file
    if not cv:
        flash(request, "Unggah CV terlebih dahulu di halaman profil atau lampirkan pada formulir lamaran.", "danger")
        return redirect(f"/lowongan/{job.slug}")
    if uploaded:
        seeker.cv_file = uploaded

    db.add(
        Application(
            job_id=job.id,
            seeker_id=seeker.id,
            cover_letter=cover_letter.strip() or None,
            cv_file=cv,
            status=ApplicationStatus.SUBMITTED,
        )
    )
    log_activity(db, user, "apply", f"Melamar '{job.title}' di {job.company.name}")
    db.commit()

    flash(request, "Lamaran berhasil dikirim. Pantau statusnya di menu Lamaran Saya.", "success")
    return redirect("/pelamar/lamaran")


@router.post("/lamaran/{app_id}/batal")
async def batalkan_lamaran(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_required),
    seeker: Seeker = Depends(current_seeker),
):
    app_obj = db.get(Application, app_id)
    if not app_obj or app_obj.seeker_id != seeker.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lamaran tidak ditemukan.")
    if app_obj.status in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED):
        flash(request, "Lamaran yang sudah final tidak dapat dibatalkan.", "warning")
        return redirect("/pelamar/lamaran")

    app_obj.status = ApplicationStatus.WITHDRAWN
    log_activity(db, user, "withdraw", f"Membatalkan lamaran #{app_obj.id}")
    db.commit()
    flash(request, "Lamaran dibatalkan.", "info")
    return redirect("/pelamar/lamaran")


@router.get("/tersimpan")
async def tersimpan(request: Request, db: Session = Depends(get_db), seeker: Seeker = Depends(current_seeker)):
    saved = (
        db.query(SavedJob)
        .options(joinedload(SavedJob.job).joinedload(Job.company))
        .filter(SavedJob.seeker_id == seeker.id)
        .order_by(SavedJob.created_at.desc())
        .all()
    )
    return render(request, "seeker/saved.html", {"saved": saved})


@router.post("/simpan/{job_id}")
async def toggle_simpan(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    seeker: Seeker = Depends(current_seeker),
    kembali: str = Form("/lowongan"),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan.")

    existing = (
        db.query(SavedJob).filter(SavedJob.job_id == job_id, SavedJob.seeker_id == seeker.id).first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        flash(request, "Lowongan dihapus dari daftar tersimpan.", "info")
    else:
        db.add(SavedJob(job_id=job_id, seeker_id=seeker.id))
        db.commit()
        flash(request, "Lowongan disimpan.", "success")
    return redirect(kembali)
