from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BKK SMK Negeri 1 Pati"
    app_env: str = "development"
    debug: bool = True
    base_url: str = "http://localhost:8000"
    secret_key: str = "dev-secret-key-please-change-me-0123456789"

    database_url: str = "postgresql+psycopg2://bkk:bkk@localhost:5432/bkk_smkn1pati"

    upload_dir: str = "app/static/uploads"
    max_upload_mb: int = 5

    admin_email: str = "admin@bkksmkn1pati.sch.id"
    admin_password: str = "Admin#12345"
    admin_name: str = "Administrator BKK"

    require_job_approval: bool = True
    require_company_verification: bool = True

    school_name: str = "SMK Negeri 1 Pati"
    school_address: str = "Jl. AKBP. R. Agil Kusumadya No.1, Pati, Jawa Tengah 59163"
    school_phone: str = "(0295) 381768"
    school_email: str = "bkk@smkn1pati.sch.id"

    @property
    def upload_path(self) -> Path:
        p = BASE_DIR / self.upload_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
