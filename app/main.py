"""Titik masuk aplikasi BKK SMK Negeri 1 Pati."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import joinedload
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app import __version__
from app.config import BASE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.deps import RedirectException
from app.models import User
from app.routers import admin, auth, company, public, seeker
from app.templating import render
from app.utils import flash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("bkk")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    log.info("Skema database siap (%s)", settings.app_env)
    yield
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Portal Bursa Kerja Khusus — perusahaan, pencari kerja, dan admin sekolah.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.middleware("http")
async def attach_current_user(request: Request, call_next):
    """Sediakan user aktif untuk semua template tanpa dependency berulang."""
    request.state.current_user = None
    uid = request.session.get("user_id")
    if uid:
        db = SessionLocal()
        try:
            # Relasi dimuat eager: objek ini dipakai template setelah sesi ditutup.
            user = (
                db.query(User)
                .options(joinedload(User.company), joinedload(User.seeker))
                .filter(User.id == uid)
                .first()
            )
            if user and user.is_active:
                request.state.current_user = user
            else:
                request.session.clear()
        finally:
            db.close()
    return await call_next(request)


# SessionMiddleware didaftarkan SETELAH middleware di atas agar berada di lapisan
# luar — Starlette menjalankan middleware dari yang terakhir didaftarkan, sehingga
# sesi sudah tersedia ketika `attach_current_user` dijalankan.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="bkk_session",
    max_age=60 * 60 * 12,
    same_site="lax",
    https_only=settings.app_env == "production",
)



@app.exception_handler(RedirectException)
async def redirect_exception_handler(request: Request, exc: RedirectException):
    flash(request, exc.message, exc.category)
    return RedirectResponse(exc.url, status_code=303)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return render(
        request,
        "error.html",
        {"code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return render(
        request,
        "error.html",
        {"code": 422, "detail": "Data yang dikirim tidak valid. Periksa kembali isian formulir."},
        status_code=422,
    )


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(seeker.router)
app.include_router(company.router)
app.include_router(admin.router)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "version": __version__, "env": settings.app_env}
