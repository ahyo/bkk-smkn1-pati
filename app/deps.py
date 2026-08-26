"""Dependency FastAPI: user aktif, penjaga peran, konteks template."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Role, Seeker, User


class RedirectException(Exception):
    def __init__(self, url: str, message: str = "Silakan masuk terlebih dahulu untuk melanjutkan.",
                 category: str = "warning"):
        self.url = url
        self.message = message
        self.category = category


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    user = db.get(User, uid)
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def login_required(request: Request, user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise RedirectException(f"/masuk?next={request.url.path}")
    return user


def require_role(*roles: Role):
    def guard(request: Request, user: User = Depends(login_required)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Anda tidak memiliki akses ke halaman ini.")
        return user

    return guard


admin_required = require_role(Role.ADMIN)
company_required = require_role(Role.COMPANY)
seeker_required = require_role(Role.SEEKER)


def current_company(
    user: User = Depends(company_required), db: Session = Depends(get_db)
) -> Company:
    company = db.query(Company).filter(Company.user_id == user.id).first()
    if not company:
        raise RedirectException(
            "/perusahaan/profil",
            "Lengkapi profil perusahaan Anda terlebih dahulu.",
            "info",
        )
    return company


def current_seeker(user: User = Depends(seeker_required), db: Session = Depends(get_db)) -> Seeker:
    seeker = db.query(Seeker).filter(Seeker.user_id == user.id).first()
    if not seeker:
        raise RedirectException(
            "/pelamar/profil", "Lengkapi profil Anda terlebih dahulu.", "info"
        )
    return seeker


def redirect(url: str, status_code: int = status.HTTP_303_SEE_OTHER) -> RedirectResponse:
    return RedirectResponse(url, status_code=status_code)
