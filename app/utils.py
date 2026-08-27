"""Utilitas umum: slug, upload berkas, format tanggal, flash message."""

from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings

BULAN = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

ALLOWED_DOC = {".pdf", ".doc", ".docx"}
ALLOWED_IMG = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text) or "item"


def unique_slug(db: Session, model, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.query(model).filter(model.slug == candidate).first():
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def tanggal(value: date | datetime | None, with_time: bool = False) -> str:
    if not value:
        return "-"
    out = f"{value.day} {BULAN[value.month]} {value.year}"
    if with_time and isinstance(value, datetime):
        out += f" · {value:%H:%M}"
    return out


def bulan_tahun(value: date | datetime | None, singkat: bool = True) -> str:
    """Label bulan untuk sumbu grafik, mis. "Mar 2026"."""
    if not value:
        return "-"
    nama = BULAN[value.month]
    return f"{nama[:3] if singkat else nama} {value.year}"


def waktu_lalu(value: datetime | None) -> str:
    if not value:
        return "-"
    now = datetime.now(tz=value.tzinfo) if value.tzinfo else datetime.now()
    delta = now - value
    detik = int(delta.total_seconds())
    if detik < 60:
        return "baru saja"
    if detik < 3600:
        return f"{detik // 60} menit lalu"
    if detik < 86400:
        return f"{detik // 3600} jam lalu"
    if detik < 2592000:
        return f"{detik // 86400} hari lalu"
    return tanggal(value)


def rupiah(value) -> str:
    if value is None:
        return "-"
    return "Rp" + f"{int(value):,}".replace(",", ".")


def save_upload(file: UploadFile | None, folder: str, allowed: set[str]) -> str | None:
    """Simpan berkas unggahan; mengembalikan path relatif terhadap /static."""
    if not file or not file.filename:
        return None

    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Format berkas {ext or '(tanpa ekstensi)'} tidak didukung. Gunakan: {', '.join(sorted(allowed))}",
        )

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Ukuran berkas melebihi {settings.max_upload_mb} MB.",
        )

    target_dir = settings.upload_path / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now():%Y%m%d}-{secrets.token_hex(6)}{ext}"
    (target_dir / name).write_bytes(data)
    return f"uploads/{folder}/{name}"


def flash(request: Request, message: str, category: str = "info") -> None:
    request.session.setdefault("_flash", []).append({"message": message, "category": category})


def pop_flash(request: Request) -> list[dict]:
    return request.session.pop("_flash", [])


def paginate(query, page: int, per_page: int = 10) -> tuple[list, dict]:
    page = max(page, 1)
    total = query.order_by(None).count()
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, {
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "start": (page - 1) * per_page + 1 if total else 0,
        "end": min(page * per_page, total),
    }
