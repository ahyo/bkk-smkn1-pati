"""Model ORM untuk sistem BKK SMK Negeri 1 Pati."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    ADMIN = "admin"
    COMPANY = "company"
    SEEKER = "seeker"


class CompanyStatus(str, enum.Enum):
    PENDING = "pending"      # menunggu verifikasi admin
    VERIFIED = "verified"    # terverifikasi, boleh memposting
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"      # menunggu persetujuan admin
    PUBLISHED = "published"
    REJECTED = "rejected"
    CLOSED = "closed"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    PART_TIME = "part_time"
    FREELANCE = "freelance"


class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


EMPLOYMENT_LABEL = {
    EmploymentType.FULL_TIME: "Penuh Waktu",
    EmploymentType.CONTRACT: "Kontrak",
    EmploymentType.INTERNSHIP: "Magang / PKL",
    EmploymentType.PART_TIME: "Paruh Waktu",
    EmploymentType.FREELANCE: "Lepas",
}

JOB_STATUS_LABEL = {
    JobStatus.DRAFT: "Draf",
    JobStatus.PENDING: "Menunggu Persetujuan",
    JobStatus.PUBLISHED: "Tayang",
    JobStatus.REJECTED: "Ditolak",
    JobStatus.CLOSED: "Ditutup",
}

APPLICATION_STATUS_LABEL = {
    ApplicationStatus.SUBMITTED: "Terkirim",
    ApplicationStatus.REVIEWED: "Diseleksi Berkas",
    ApplicationStatus.SHORTLISTED: "Masuk Shortlist",
    ApplicationStatus.INTERVIEW: "Panggilan Wawancara",
    ApplicationStatus.ACCEPTED: "Diterima",
    ApplicationStatus.REJECTED: "Tidak Lolos",
    ApplicationStatus.WITHDRAWN: "Dibatalkan Pelamar",
}

COMPANY_STATUS_LABEL = {
    CompanyStatus.PENDING: "Menunggu Verifikasi",
    CompanyStatus.VERIFIED: "Terverifikasi",
    CompanyStatus.REJECTED: "Ditolak",
    CompanyStatus.SUSPENDED: "Dinonaktifkan",
}

# Data awal kompetensi keahlian SMK N 1 Pati. Dipakai sekali saat pengisian
# tabel `majors`; setelah itu jurusan dikelola lewat menu admin.
DEFAULT_MAJORS: list[tuple[str, str]] = [
    ("AKL", "Akuntansi dan Keuangan Lembaga"),
    ("MPLB", "Manajemen Perkantoran dan Layanan Bisnis"),
    ("BDP", "Bisnis Daring dan Pemasaran"),
    ("TKJ", "Teknik Komputer dan Jaringan"),
    ("RPL", "Rekayasa Perangkat Lunak"),
    ("DKV", "Multimedia / Desain Komunikasi Visual"),
    ("PHT", "Perhotelan"),
    ("KUL", "Kuliner"),
    ("LN", "Lainnya"),
]


class Major(Base):
    """Kompetensi keahlian (jurusan) yang dibuka sekolah.

    Dijadikan tabel tersendiri, bukan teks bebas, supaya laporan serapan kerja
    per jurusan tidak pecah gara-gara perbedaan penulisan.
    """

    __tablename__ = "majors"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seekers: Mapped[list[Seeker]] = relationship(back_populates="major")
    jobs: Mapped[list[Job]] = relationship(back_populates="major")

    def __str__(self) -> str:
        # Membuat {{ seeker.major }} di template tetap mencetak nama jurusan.
        return self.name


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped[Company | None] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    seeker: Mapped[Seeker | None] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        if self.role == Role.COMPANY and self.company:
            return self.company.name
        return self.full_name


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(200))
    contact_person: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    logo: Mapped[str | None] = mapped_column(String(255))
    employee_count: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, name="company_status_enum"), default=CompanyStatus.PENDING, index=True
    )
    verification_note: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="company")
    jobs: Mapped[list[Job]] = relationship(back_populates="company", cascade="all, delete-orphan")

    @property
    def is_verified(self) -> bool:
        return self.status == CompanyStatus.VERIFIED

    @property
    def initials(self) -> str:
        parts = [p for p in (self.name or "?").split() if p[:1].isalnum()]
        return "".join(p[0].upper() for p in parts[:2]) or "?"


class Seeker(Base):
    __tablename__ = "seekers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    nis: Mapped[str | None] = mapped_column(String(30), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    gender: Mapped[str | None] = mapped_column(String(10))          # L / P
    birth_place: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    major_id: Mapped[int | None] = mapped_column(
        ForeignKey("majors.id", ondelete="SET NULL"), index=True
    )
    graduation_year: Mapped[int | None] = mapped_column(Integer, index=True)
    is_alumni: Mapped[bool] = mapped_column(Boolean, default=True)
    headline: Mapped[str | None] = mapped_column(String(180))
    summary: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)                # dipisah koma
    experience: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    photo: Mapped[str | None] = mapped_column(String(255))
    cv_file: Mapped[str | None] = mapped_column(String(255))
    open_to_work: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="seeker")
    major: Mapped[Major | None] = relationship(back_populates="seekers")
    applications: Mapped[list[Application]] = relationship(back_populates="seeker", cascade="all, delete-orphan")
    saved_jobs: Mapped[list[SavedJob]] = relationship(back_populates="seeker", cascade="all, delete-orphan")

    @property
    def skill_list(self) -> list[str]:
        return [s.strip() for s in (self.skills or "").split(",") if s.strip()]

    @property
    def completeness(self) -> int:
        """Persentase kelengkapan profil — dipakai untuk nudge di dashboard."""
        fields = [
            self.phone, self.gender, self.birth_date, self.address, self.city,
            self.major_id, self.graduation_year, self.headline, self.summary,
            self.skills, self.education, self.cv_file, self.photo,
        ]
        filled = sum(1 for f in fields if f)
        return round(filled / len(fields) * 100)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    major_id: Mapped[int | None] = mapped_column(
        ForeignKey("majors.id", ondelete="SET NULL"), index=True
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type_enum"), default=EmploymentType.FULL_TIME, index=True
    )
    location: Mapped[str] = mapped_column(String(150), index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    quota: Mapped[int] = mapped_column(Integer, default=1)
    min_education: Mapped[str | None] = mapped_column(String(60), default="SMK/SMA Sederajat")
    max_age: Mapped[int | None] = mapped_column(Integer)
    gender_pref: Mapped[str | None] = mapped_column(String(20))     # Semua / L / P
    deadline: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"), default=JobStatus.PENDING, index=True
    )
    review_note: Mapped[str | None] = mapped_column(Text)
    views: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[Company] = relationship(back_populates="jobs")
    major: Mapped[Major | None] = relationship(back_populates="jobs")
    applications: Mapped[list[Application]] = relationship(back_populates="job", cascade="all, delete-orphan")

    @property
    def is_expired(self) -> bool:
        return bool(self.deadline and self.deadline < date.today())

    @property
    def is_open(self) -> bool:
        return self.status == JobStatus.PUBLISHED and not self.is_expired

    @property
    def salary_display(self) -> str:
        if self.salary_hidden or (not self.salary_min and not self.salary_max):
            return "Negosiasi"

        def rp(v: float | None) -> str:
            return f"Rp{int(v):,}".replace(",", ".")

        if self.salary_min and self.salary_max:
            return f"{rp(self.salary_min)} – {rp(self.salary_max)}"
        return rp(self.salary_min or self.salary_max)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "seeker_id", name="uq_application_job_seeker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id", ondelete="CASCADE"), index=True)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    cv_file: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"),
        default=ApplicationStatus.SUBMITTED,
        index=True,
    )
    company_note: Mapped[str | None] = mapped_column(Text)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="applications")
    seeker: Mapped[Seeker] = relationship(back_populates="applications")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("job_id", "seeker_id", name="uq_saved_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job] = relationship()
    seeker: Mapped[Seeker] = relationship(back_populates="saved_jobs")


class Announcement(Base):
    """Pengumuman BKK yang tampil di beranda publik."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActivityLog(Base):
    """Jejak audit ringan untuk pemantauan admin."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor: Mapped[str | None] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
