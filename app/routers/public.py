"""Halaman publik: beranda, daftar lowongan, detail, profil perusahaan mitra."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Announcement,
    Application,
    Company,
    Major,
    CompanyStatus,
    EmploymentType,
    Job,
    JobStatus,
    Role,
    SavedJob,
    Seeker,
    User,
)
from app.templating import render
from app.utils import daftar_jurusan, paginate

router = APIRouter(tags=["publik"])


def published_jobs(db: Session):
    """Query dasar lowongan yang boleh dilihat publik."""
    return (
        db.query(Job)
        .join(Company)
        .options(joinedload(Job.company))
        .filter(Job.status == JobStatus.PUBLISHED)
        .filter(Company.status == CompanyStatus.VERIFIED)
        .filter(or_(Job.deadline.is_(None), Job.deadline >= date.today()))
    )


@router.get("/")
async def beranda(request: Request, db: Session = Depends(get_db)):
    jobs = published_jobs(db).order_by(Job.published_at.desc().nullslast(), Job.id.desc()).limit(6).all()

    stats = {
        "lowongan": published_jobs(db).count(),
        "perusahaan": db.query(Company).filter(Company.status == CompanyStatus.VERIFIED).count(),
        "pelamar": db.query(Seeker).count(),
        "penempatan": db.query(Application)
        .filter(Application.status == "accepted")
        .count(),
    }

    top_majors = (
        published_jobs(db)
        .outerjoin(Major, Job.major_id == Major.id)
        .with_entities(Major.name, Major.slug, func.count(Job.id))
        .group_by(Major.name, Major.slug)
        .order_by(func.count(Job.id).desc())
        .limit(6)
        .all()
    )

    partners = (
        db.query(Company)
        .filter(Company.status == CompanyStatus.VERIFIED)
        .order_by(Company.created_at.desc())
        .limit(12)
        .all()
    )

    announcements = (
        db.query(Announcement)
        .filter(Announcement.is_published.is_(True))
        .order_by(Announcement.created_at.desc())
        .limit(3)
        .all()
    )

    return render(
        request,
        "public/index.html",
        {
            "jobs": jobs,
            "stats": stats,
            "top_majors": [(nama or "Semua jurusan", slug or "", c) for nama, slug, c in top_majors],
            "partners": partners,
            "announcements": announcements,
            "majors": daftar_jurusan(db),
        },
    )


@router.get("/lowongan")
async def daftar_lowongan(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query("", description="Kata kunci"),
    lokasi: str = "",
    jurusan: str = "",
    tipe: str = "",
    urut: str = "terbaru",
    page: int = 1,
):
    query = published_jobs(db)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Job.title.ilike(like), Job.description.ilike(like), Company.name.ilike(like)))
    if lokasi:
        query = query.filter(Job.location.ilike(f"%{lokasi.strip()}%"))
    if jurusan:
        query = query.join(Major, Job.major_id == Major.id).filter(Major.slug == jurusan)
    if tipe:
        try:
            query = query.filter(Job.employment_type == EmploymentType(tipe))
        except ValueError:
            pass

    if urut == "gaji":
        query = query.order_by(Job.salary_max.desc().nullslast(), Job.id.desc())
    elif urut == "deadline":
        query = query.order_by(Job.deadline.asc().nullslast(), Job.id.desc())
    else:
        query = query.order_by(Job.published_at.desc().nullslast(), Job.id.desc())

    jobs, meta = paginate(query, page, per_page=10)

    locations = [
        r[0]
        for r in published_jobs(db).with_entities(Job.location).distinct().order_by(Job.location).all()
        if r[0]
    ]

    return render(
        request,
        "public/jobs.html",
        {
            "jobs": jobs,
            "meta": meta,
            "filters": {"q": q, "lokasi": lokasi, "jurusan": jurusan, "tipe": tipe, "urut": urut},
            "locations": locations,
            "majors": daftar_jurusan(db),
        },
    )


@router.get("/lowongan/{slug}")
async def detail_lowongan(slug: str, request: Request, db: Session = Depends(get_db)):
    job = (
        db.query(Job)
        .options(joinedload(Job.company))
        .filter(Job.slug == slug)
        .first()
    )
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan tidak ditemukan atau sudah dihapus.")

    user: User | None = request.state.current_user
    is_owner = bool(user and user.role == Role.COMPANY and user.company and user.company.id == job.company_id)
    is_admin = bool(user and user.role == Role.ADMIN)
    if job.status != JobStatus.PUBLISHED and not (is_owner or is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lowongan belum tayang.")

    # Hitung view hanya untuk pengunjung non-pemilik.
    if not (is_owner or is_admin):
        job.views = (job.views or 0) + 1
        db.commit()

    sudah_melamar = tersimpan = False
    if user and user.role == Role.SEEKER and user.seeker:
        sudah_melamar = bool(
            db.query(Application)
            .filter(Application.job_id == job.id, Application.seeker_id == user.seeker.id)
            .first()
        )
        tersimpan = bool(
            db.query(SavedJob)
            .filter(SavedJob.job_id == job.id, SavedJob.seeker_id == user.seeker.id)
            .first()
        )

    related = (
        published_jobs(db)
        .filter(Job.id != job.id)
        .filter(or_(Job.major_id == job.major_id, Job.company_id == job.company_id))
        .order_by(Job.published_at.desc().nullslast())
        .limit(4)
        .all()
    )

    return render(
        request,
        "public/job_detail.html",
        {
            "job": job,
            "sudah_melamar": sudah_melamar,
            "tersimpan": tersimpan,
            "related": related,
            "jumlah_pelamar": db.query(Application).filter(Application.job_id == job.id).count(),
        },
    )


@router.get("/perusahaan-mitra")
async def daftar_perusahaan(request: Request, db: Session = Depends(get_db), q: str = "", page: int = 1):
    query = db.query(Company).filter(Company.status == CompanyStatus.VERIFIED)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Company.name.ilike(like), Company.industry.ilike(like), Company.city.ilike(like)))
    query = query.order_by(Company.name)
    companies, meta = paginate(query, page, per_page=12)

    counts = dict(
        published_jobs(db)
        .with_entities(Job.company_id, func.count(Job.id))
        .group_by(Job.company_id)
        .all()
    )
    return render(
        request,
        "public/companies.html",
        {"companies": companies, "meta": meta, "q": q, "counts": counts},
    )


@router.get("/perusahaan-mitra/{slug}")
async def detail_perusahaan(slug: str, request: Request, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company or company.status != CompanyStatus.VERIFIED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Perusahaan mitra tidak ditemukan.")
    jobs = published_jobs(db).filter(Job.company_id == company.id).order_by(Job.id.desc()).all()
    return render(request, "public/company_detail.html", {"company": company, "jobs": jobs})


@router.get("/tentang")
async def tentang(request: Request, db: Session = Depends(get_db)):
    stats = {
        "lowongan": published_jobs(db).count(),
        "perusahaan": db.query(Company).filter(Company.status == CompanyStatus.VERIFIED).count(),
        "pelamar": db.query(Seeker).count(),
    }
    return render(request, "public/about.html", {"stats": stats})
