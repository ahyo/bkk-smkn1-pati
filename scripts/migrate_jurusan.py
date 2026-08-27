#!/usr/bin/env python3
"""Migrasi jurusan dari teks bebas menjadi tabel master `majors`.

Versi sebelumnya menyimpan jurusan sebagai teks pada `seekers.major` dan
`jobs.major_target`. Skrip ini memindahkannya ke tabel `majors` dan mengganti
kolom lama dengan kunci asing, tanpa kehilangan data yang sudah masuk.

Aman dijalankan berulang: langkah yang sudah selesai akan dilewati.

    python scripts/migrate_jurusan.py            # lihat rencana, tidak menulis
    python scripts/migrate_jurusan.py --terapkan # jalankan
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import DEFAULT_MAJORS, Major  # noqa: E402
from app.utils import slugify  # noqa: E402


def kolom(tabel: str) -> set[str]:
    insp = inspect(engine)
    if tabel not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(tabel)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--terapkan", action="store_true", help="tulis perubahan ke database")
    args = ap.parse_args()
    tulis = args.terapkan

    print(f"Mode: {'TERAPKAN' if tulis else 'PRATINJAU (tidak menulis)'}\n")

    # 1) Pastikan tabel majors ada.
    Base.metadata.create_all(bind=engine, tables=[Major.__table__])
    print("1. Tabel `majors` tersedia.")

    db = SessionLocal()
    try:
        # 2) Kumpulkan nama jurusan yang sudah terpakai di data lama.
        kol_seeker, kol_job = kolom("seekers"), kolom("jobs")
        terpakai: set[str] = set()
        if "major" in kol_seeker:
            terpakai |= {
                r[0].strip()
                for r in db.execute(text("SELECT DISTINCT major FROM seekers WHERE major IS NOT NULL"))
                if r[0] and r[0].strip()
            }
        if "major_target" in kol_job:
            terpakai |= {
                r[0].strip()
                for r in db.execute(text("SELECT DISTINCT major_target FROM jobs WHERE major_target IS NOT NULL"))
                if r[0] and r[0].strip()
            }
        print(f"2. Nama jurusan ditemukan pada data lama: {len(terpakai)}")

        # 3) Isi tabel majors: data baku dulu, lalu nama lain yang terlanjur dipakai.
        ada = {m.name: m for m in db.query(Major).all()}
        baru = 0
        for urutan, (kode, nama) in enumerate(DEFAULT_MAJORS):
            if nama in ada:
                continue
            if tulis:
                db.add(Major(code=kode, name=nama, slug=slugify(nama), sort_order=urutan))
            baru += 1

        baku = {n for _, n in DEFAULT_MAJORS}
        for i, nama in enumerate(sorted(terpakai - baku - set(ada))):
            kode = (slugify(nama).upper().replace("-", "")[:8] or f"J{i}")
            if tulis:
                db.add(Major(code=kode, name=nama, slug=slugify(nama), sort_order=900 + i))
            baru += 1
            print(f"   · jurusan di luar daftar baku dipertahankan: {nama} (kode {kode})")
        if tulis:
            db.commit()
        print(f"3. Baris jurusan baru: {baru}")

        peta = {m.name: m.id for m in db.query(Major).all()} if tulis else {}

        # 4) Tambah kolom kunci asing bila belum ada, lalu petakan nilai lama.
        for tabel, kolom_lama in (("seekers", "major"), ("jobs", "major_target")):
            kols = kolom(tabel)
            if "major_id" not in kols:
                print(f"4. {tabel}: menambah kolom major_id")
                if tulis:
                    db.execute(text(
                        f"ALTER TABLE {tabel} ADD COLUMN major_id INTEGER "
                        f"REFERENCES majors(id) ON DELETE SET NULL"
                    ))
                    db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{tabel}_major_id ON {tabel}(major_id)"))
                    db.commit()
            else:
                print(f"4. {tabel}: kolom major_id sudah ada")

            if kolom_lama in kols:
                if tulis:
                    dipetakan = 0
                    for nama, mid in peta.items():
                        hasil = db.execute(
                            text(f"UPDATE {tabel} SET major_id = :mid "
                                 f"WHERE major_id IS NULL AND TRIM({kolom_lama}) = :nama"),
                            {"mid": mid, "nama": nama},
                        )
                        dipetakan += hasil.rowcount or 0
                    db.commit()
                    print(f"   · {tabel}: {dipetakan} baris dipetakan dari `{kolom_lama}`")

                    sisa = db.execute(text(
                        f"SELECT COUNT(*) FROM {tabel} "
                        f"WHERE major_id IS NULL AND {kolom_lama} IS NOT NULL AND TRIM({kolom_lama}) <> ''"
                    )).scalar()
                    if sisa:
                        print(f"   ! {tabel}: {sisa} baris tidak terpetakan — kolom lama TIDAK dihapus.")
                        continue

                    db.execute(text(f"ALTER TABLE {tabel} DROP COLUMN {kolom_lama}"))
                    db.commit()
                    print(f"   · {tabel}: kolom lama `{kolom_lama}` dihapus")
                else:
                    print(f"   · {tabel}: kolom lama `{kolom_lama}` akan dipetakan lalu dihapus")
            else:
                print(f"   · {tabel}: kolom lama `{kolom_lama}` sudah tidak ada")

        print("\nSelesai." if tulis else "\nPratinjau selesai. Jalankan ulang dengan --terapkan.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
