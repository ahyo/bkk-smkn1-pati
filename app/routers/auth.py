"""Autentikasi: masuk, keluar, registrasi pencari kerja & perusahaan, ganti sandi."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import login_required, redirect
from app.models import ActivityLog, Company, CompanyStatus, Interest, Role, Seeker, User
from app.security import hash_password, password_issues, verify_password
from app.templating import render
from app.utils import daftar_jurusan, flash, unique_slug

router = APIRouter(tags=["auth"])

HOME_BY_ROLE = {
    Role.ADMIN: "/admin",
    Role.COMPANY: "/perusahaan",
    Role.SEEKER: "/pelamar",
}


def log_activity(db: Session, user: User | None, action: str, detail: str = "") -> None:
    db.add(
        ActivityLog(
            user_id=user.id if user else None,
            actor=user.display_name if user else "Anonim",
            action=action,
            detail=detail,
        )
    )


@router.get("/masuk")
async def form_masuk(request: Request, next: str = ""):
    if request.state.current_user:
        return redirect(HOME_BY_ROLE[request.state.current_user.role])
    return render(request, "auth/login.html", {"next": next})


@router.post("/masuk")
async def proses_masuk(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
):
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        flash(request, "Email atau kata sandi salah.", "danger")
        return render(request, "auth/login.html", {"next": next, "email": email}, status_code=401)

    if not user.is_active:
        flash(request, "Akun Anda dinonaktifkan. Hubungi admin BKK sekolah.", "danger")
        return render(request, "auth/login.html", {"email": email}, status_code=403)

    request.session.clear()
    request.session["user_id"] = user.id
    user.last_login_at = datetime.now()
    log_activity(db, user, "login", f"Masuk sebagai {user.role.value}")
    db.commit()

    flash(request, f"Selamat datang, {user.display_name}!", "success")
    return redirect(next or HOME_BY_ROLE[user.role])


@router.get("/keluar")
@router.post("/keluar")
async def keluar(request: Request):
    request.session.clear()
    return redirect("/masuk")


@router.get("/daftar")
async def pilih_pendaftaran(request: Request):
    if request.state.current_user:
        return redirect(HOME_BY_ROLE[request.state.current_user.role])
    return render(request, "auth/register_choice.html")


# ── Registrasi pencari kerja ────────────────────────────────────────────────

@router.get("/daftar/pencari-kerja")
async def form_daftar_pelamar(request: Request, db: Session = Depends(get_db)):
    return render(request, "auth/register_seeker.html", {"form": {}, "majors": daftar_jurusan(db)})


@router.post("/daftar/pencari-kerja")
async def proses_daftar_pelamar(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    nis: str = Form(""),
    class_name: str = Form(""),
    major_id: str = Form(""),
    graduation_year: str = Form(""),
    interest: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    agree: str = Form(""),
):
    form = {
        "full_name": full_name, "email": email, "phone": phone,
        "nis": nis, "class_name": class_name, "major_id": major_id,
        "graduation_year": graduation_year, "interest": interest,
    }
    email = email.strip().lower()
    errors: list[str] = []

    if db.query(User).filter(User.email == email).first():
        errors.append("Email sudah terdaftar. Silakan masuk atau gunakan email lain.")
    if password != password_confirm:
        errors.append("Konfirmasi kata sandi tidak cocok.")
    errors += password_issues(password)
    if not agree:
        errors.append("Anda harus menyetujui ketentuan penggunaan portal.")

    if errors:
        for e in errors:
            flash(request, e, "danger")
        return render(
            request, "auth/register_seeker.html",
            {"form": form, "majors": daftar_jurusan(db)}, status_code=400,
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=Role.SEEKER,
    )
    db.add(user)
    db.flush()

    db.add(
        Seeker(
            user_id=user.id,
            phone=phone.strip() or None,
            nis=nis.strip() or None,
            class_name=class_name.strip() or None,
            major_id=int(major_id) if major_id.isdigit() else None,
            graduation_year=int(graduation_year) if graduation_year.isdigit() else None,
            interest=Interest(interest) if interest in Interest._value2member_map_ else None,
        )
    )
    log_activity(db, user, "register_seeker", "Pendaftaran akun pencari kerja")
    db.commit()

    request.session["user_id"] = user.id
    flash(request, "Akun berhasil dibuat. Lengkapi profil Anda agar mudah dilirik perusahaan.", "success")
    return redirect("/pelamar/profil")


# ── Registrasi perusahaan ───────────────────────────────────────────────────

@router.get("/daftar/perusahaan")
async def form_daftar_perusahaan(request: Request):
    return render(request, "auth/register_company.html", {"form": {}})


@router.post("/daftar/perusahaan")
async def proses_daftar_perusahaan(
    request: Request,
    db: Session = Depends(get_db),
    company_name: str = Form(...),
    contact_person: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    industry: str = Form(""),
    city: str = Form(""),
    address: str = Form(""),
    website: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    agree: str = Form(""),
):
    form = {
        "company_name": company_name, "contact_person": contact_person, "email": email,
        "phone": phone, "industry": industry, "city": city, "address": address, "website": website,
    }
    email = email.strip().lower()
    errors: list[str] = []

    if db.query(User).filter(User.email == email).first():
        errors.append("Email sudah terdaftar.")
    if password != password_confirm:
        errors.append("Konfirmasi kata sandi tidak cocok.")
    errors += password_issues(password)
    if not agree:
        errors.append("Anda harus menyetujui ketentuan kerja sama BKK.")

    if errors:
        for e in errors:
            flash(request, e, "danger")
        return render(request, "auth/register_company.html", {"form": form}, status_code=400)

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=contact_person.strip(),
        role=Role.COMPANY,
    )
    db.add(user)
    db.flush()

    db.add(
        Company(
            user_id=user.id,
            name=company_name.strip(),
            slug=unique_slug(db, Company, company_name),
            contact_person=contact_person.strip(),
            phone=phone.strip() or None,
            industry=industry.strip() or None,
            city=city.strip() or None,
            address=address.strip() or None,
            website=website.strip() or None,
            status=CompanyStatus.PENDING,
        )
    )
    log_activity(db, user, "register_company", f"Pendaftaran perusahaan {company_name}")
    db.commit()

    request.session["user_id"] = user.id
    flash(
        request,
        "Pendaftaran diterima. Akun menunggu verifikasi admin BKK sebelum dapat memposting lowongan.",
        "success",
    )
    return redirect("/perusahaan")


# ── Ganti kata sandi ────────────────────────────────────────────────────────

@router.get("/akun/kata-sandi")
async def form_ganti_sandi(request: Request, user: User = Depends(login_required)):
    return render(request, "auth/change_password.html")


@router.post("/akun/kata-sandi")
async def proses_ganti_sandi(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(login_required),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    errors: list[str] = []
    if not verify_password(current_password, user.password_hash):
        errors.append("Kata sandi saat ini salah.")
    if new_password != confirm_password:
        errors.append("Konfirmasi kata sandi baru tidak cocok.")
    errors += password_issues(new_password)

    if errors:
        for e in errors:
            flash(request, e, "danger")
        return render(request, "auth/change_password.html", status_code=400)

    user.password_hash = hash_password(new_password)
    log_activity(db, user, "change_password", "Kata sandi diperbarui")
    db.commit()
    flash(request, "Kata sandi berhasil diperbarui.", "success")
    return redirect(HOME_BY_ROLE[user.role])
