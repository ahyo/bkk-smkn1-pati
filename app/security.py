"""Hashing password + helper sesi berbasis cookie tertandatangani."""

from __future__ import annotations

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw, hashed)
    except ValueError:
        return False


def password_issues(raw: str) -> list[str]:
    """Validasi kekuatan password minimal untuk portal publik."""
    problems: list[str] = []
    if len(raw) < 8:
        problems.append("Kata sandi minimal 8 karakter.")
    if not any(c.isalpha() for c in raw):
        problems.append("Kata sandi harus memuat huruf.")
    if not any(c.isdigit() for c in raw):
        problems.append("Kata sandi harus memuat angka.")
    return problems
