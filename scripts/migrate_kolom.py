#!/usr/bin/env python3
"""Tambahkan kolom yang ada di model tetapi belum ada di database.

`Base.metadata.create_all()` hanya membuat tabel baru — kolom yang ditambahkan
kemudian pada model tidak ikut dibuat, sehingga pemasangan lama akan error.
Skrip ini menutup celah itu.

Hanya melakukan ADD COLUMN untuk kolom yang boleh NULL atau punya nilai baku;
tidak pernah menghapus, mengubah tipe, atau menulis ulang data. Kolom yang
wajib diisi (NOT NULL tanpa default) dilaporkan tetapi tidak disentuh, karena
perubahan itu butuh keputusan soal nilai untuk baris yang sudah ada.

    python scripts/migrate_kolom.py            # pratinjau
    python scripts/migrate_kolom.py --terapkan # jalankan
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

from app.database import Base, engine  # noqa: E402
import app.models  # noqa: F401,E402  (mendaftarkan seluruh model)


def tipe_sql(kolom) -> str:
    return kolom.type.compile(dialect=engine.dialect)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--terapkan", action="store_true", help="tulis perubahan ke database")
    args = ap.parse_args()
    tulis = args.terapkan

    print(f"Mode: {'TERAPKAN' if tulis else 'PRATINJAU (tidak menulis)'}\n")
    insp = inspect(engine)
    tabel_ada = set(insp.get_table_names())

    ditambah = dilewati = 0
    with engine.begin() as conn:
        for nama_tabel, tabel in Base.metadata.tables.items():
            if nama_tabel not in tabel_ada:
                print(f"{nama_tabel}: tabel belum ada — dibuat oleh create_all()")
                if tulis:
                    conn.execute(text(str(CreateTable(tabel).compile(engine))))
                continue

            kolom_db = {c["name"] for c in insp.get_columns(nama_tabel)}
            kurang = [c for c in tabel.columns if c.name not in kolom_db]
            if not kurang:
                continue

            print(f"{nama_tabel}:")
            for kol in kurang:
                wajib = not kol.nullable and kol.default is None and kol.server_default is None
                if wajib:
                    print(f"   ! {kol.name} ({tipe_sql(kol)}) WAJIB ISI — dilewati, perlu ditangani manual")
                    dilewati += 1
                    continue

                ddl = f"ALTER TABLE {nama_tabel} ADD COLUMN {kol.name} {tipe_sql(kol)}"
                print(f"   + {kol.name} ({tipe_sql(kol)})")
                if tulis:
                    # Tipe enum harus dibuat lebih dulu di PostgreSQL.
                    if hasattr(kol.type, "enums"):
                        kol.type.create(conn, checkfirst=True)
                    conn.execute(text(ddl))
                ditambah += 1

    print(f"\nKolom ditambahkan: {ditambah}" + (f" · dilewati: {dilewati}" if dilewati else ""))
    if not tulis and ditambah:
        print("Jalankan ulang dengan --terapkan untuk menerapkannya.")
    elif not ditambah:
        print("Database sudah sesuai dengan model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
