"""Konfigurasi Jinja2 terpusat: filter, global, dan helper render."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import __version__
from app.config import settings
from app.models import (
    APPLICATION_STATUS_LABEL,
    COMPANY_STATUS_LABEL,
    EMPLOYMENT_LABEL,
    JOB_STATUS_LABEL,
    MAJORS,
    ApplicationStatus,
    CompanyStatus,
    EmploymentType,
    JobStatus,
    Role,
)
from app.utils import pop_flash, rupiah, tanggal, waktu_lalu

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

BADGE_JOB = {
    JobStatus.DRAFT: "muted",
    JobStatus.PENDING: "warn",
    JobStatus.PUBLISHED: "ok",
    JobStatus.REJECTED: "danger",
    JobStatus.CLOSED: "muted",
}
BADGE_APP = {
    ApplicationStatus.SUBMITTED: "info",
    ApplicationStatus.REVIEWED: "info",
    ApplicationStatus.SHORTLISTED: "warn",
    ApplicationStatus.INTERVIEW: "warn",
    ApplicationStatus.ACCEPTED: "ok",
    ApplicationStatus.REJECTED: "danger",
    ApplicationStatus.WITHDRAWN: "muted",
}
BADGE_COMPANY = {
    CompanyStatus.PENDING: "warn",
    CompanyStatus.VERIFIED: "ok",
    CompanyStatus.REJECTED: "danger",
    CompanyStatus.SUSPENDED: "muted",
}


def _enum_value(v):
    return v.value if hasattr(v, "value") else v


templates.env.filters.update(
    tanggal=tanggal,
    tanggal_jam=lambda v: tanggal(v, with_time=True),
    waktu_lalu=waktu_lalu,
    rupiah=rupiah,
    label_kerja=lambda v: EMPLOYMENT_LABEL.get(v, _enum_value(v)),
    label_status_lowongan=lambda v: JOB_STATUS_LABEL.get(v, _enum_value(v)),
    label_status_lamaran=lambda v: APPLICATION_STATUS_LABEL.get(v, _enum_value(v)),
    label_status_perusahaan=lambda v: COMPANY_STATUS_LABEL.get(v, _enum_value(v)),
    badge_lowongan=lambda v: BADGE_JOB.get(v, "muted"),
    badge_lamaran=lambda v: BADGE_APP.get(v, "muted"),
    badge_perusahaan=lambda v: BADGE_COMPANY.get(v, "muted"),
    nl2br=lambda v: (v or "").replace("\n", "<br>"),
)

templates.env.globals.update(
    settings=settings,
    app_version=__version__,
    MAJORS=MAJORS,
    Role=Role,
    JobStatus=JobStatus,
    ApplicationStatus=ApplicationStatus,
    CompanyStatus=CompanyStatus,
    EmploymentType=EmploymentType,
    EMPLOYMENT_LABEL=EMPLOYMENT_LABEL,
    APPLICATION_STATUS_LABEL=APPLICATION_STATUS_LABEL,
    JOB_STATUS_LABEL=JOB_STATUS_LABEL,
)


def render(request: Request, name: str, ctx: dict | None = None, status_code: int = 200):
    data = {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
        "flashes": pop_flash(request),
    }
    data.update(ctx or {})
    return templates.TemplateResponse(request, name, data, status_code=status_code)
