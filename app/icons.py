"""Sistem ikon SVG inline.

Ikon digambar dengan garis (stroke) 1.6px pada kanvas 24×24 dan mewarisi warna
teks lewat `currentColor`, sehingga menyatu dengan tipografi di sekitarnya dan
tidak bergantung pada pustaka atau berkas font eksternal.
"""

from __future__ import annotations

from markupsafe import Markup

# Setiap entri adalah isi elemen <svg>; atribut umum diterapkan oleh render().
_PATHS: dict[str, str] = {
    # ── Lokasi, pekerjaan, pendidikan ──────────────────────────────────────
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/>'
                 '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "cap": '<path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12v4.5c0 1.7 2.7 3 6 3s6-1.3 6-3V12"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "money": '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>'
             '<path d="M6 12h.01M18 12h.01"/>',
    "building": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/>'
                '<path d="M9 6h.01M15 6h.01M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/>',
    "factory": '<path d="M3 21V10.5l6 3.5v-3.5l6 3.5V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v15Z"/>'
               '<path d="M7 21v-3M12 21v-3M17 21v-3"/>',

    # ── Waktu & aktivitas ──────────────────────────────────────────────────
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3 2"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "history": '<path d="M3 12a9 9 0 1 0 2.6-6.4"/><path d="M3 4v4h4"/><path d="M12 8v4.5l3 1.8"/>',

    # ── Aksi ───────────────────────────────────────────────────────────────
    "bookmark": '<path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    "bookmark-filled": '<path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" fill="currentColor"/>',
    "send": '<path d="M21.5 2.5 11 13"/><path d="M21.5 2.5 15 21l-4-8-8-4Z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "download": '<path d="M12 3.5v12"/><path d="m7.5 11.5 4.5 4.5 4.5-4.5"/><path d="M5 20.5h14"/>',
    "printer": '<path d="M6 9V3h12v6"/>'
               '<path d="M6 18H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"/>'
               '<rect x="6" y="14" width="12" height="8" rx="1"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>'
             '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/>',
    "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
                '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    "key": '<circle cx="7.5" cy="12" r="4"/><path d="M11.5 12H21"/>'
           '<path d="M17.5 12v3.5"/><path d="M20.5 12v2.5"/>',
    "settings": '<path d="M4 21v-6M4 11V3M12 21v-9M12 8V3M20 21v-4M20 13V3"/>'
                '<path d="M1.5 15h5M9.5 8h5M17.5 17h5"/>',

    # ── Status & umpan balik ───────────────────────────────────────────────
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.3 2.4 2.4 4.6-5"/>',
    "verified": '<path d="m12 2 2.4 1.8 3-.3 1 2.8 2.6 1.5-.9 2.9.9 2.9-2.6 1.5-1 2.8-3-.3L12 22l-2.4-1.8-3 .3-1-2.8L3 16.2l.9-2.9L3 10.4l2.6-1.5 1-2.8 3 .3Z" '
                'fill="currentColor" stroke="none"/><path d="m8.6 12.2 2.3 2.3 4.5-4.8" stroke="#fff" stroke-width="2"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.5h.01"/>',
    "warning": '<path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>'
               '<path d="M12 9v4.5"/><path d="M12 17.5h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5h.01"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "shield": '<path d="M12 22s8-4 8-10V5.5L12 2.5 4 5.5V12c0 6 8 10 8 10Z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',

    # ── Dokumen & komunikasi ───────────────────────────────────────────────
    "file": '<path d="M14 2.5H6.5a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8Z"/>'
            '<path d="M14 2.5V8h5.5"/><path d="M9 13.5h6M9 17h4"/>',
    "clipboard": '<path d="M9 4H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/>'
                 '<rect x="9" y="2.5" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/>',
    "inbox": '<path d="M22 12.5h-5.5l-1.5 3h-6l-1.5-3H2"/>'
             '<path d="M5.6 5.2 2 12.5V18a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5.5l-3.6-7.3A2 2 0 0 0 16.6 4H7.4a2 2 0 0 0-1.8 1.2Z"/>',
    "mail": '<rect x="2" y="4.5" width="20" height="15" rx="2"/><path d="m2.5 6.5 9.5 6 9.5-6"/>',
    "phone": '<path d="M21.5 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-6-6A19.8 19.8 0 0 1 1.6 4.2 2 2 0 0 1 3.6 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.6a2 2 0 0 1-.5 2.1L7.5 9.7a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.8.3 1.7.6 2.6.7a2 2 0 0 1 1.7 2Z"/>',
    "message": '<path d="M21 14.5a2 2 0 0 1-2 2H7.5L3.5 20.5V5a2 2 0 0 1 2-2h13.5a2 2 0 0 1 2 2z"/>',
    "megaphone": '<path d="m3 11 15-6.5v15L3 13z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/><path d="M19.5 8.5a3 3 0 0 1 0 6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>'
             '<path d="M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8.5a2 2 0 0 0-2-2h-7l-2-2.5H4a2 2 0 0 0-2 2V18a2 2 0 0 0 2 2Z"/>',

    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/>'
            '<path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>',
    "rocket": '<path d="M5 13c-1.5 1.3-2 5.5-2 5.5s4.2-.5 5.5-2"/>'
              '<path d="M12.5 18.5 9 15l-3.5-3.5C9 5.5 14 3 19.5 3.5 20 9 17.5 14 12.5 18.5Z"/>'
              '<circle cx="14.5" cy="8.5" r="1.8"/>',
    "lock": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
            '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',

    # ── Analitik ───────────────────────────────────────────────────────────
    "chart": '<path d="M3 21h18"/><path d="M7 21v-9M12 21V5M17 21v-6"/>',
    "trending": '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
}

# Ukuran baku per konteks penggunaan (piksel).
_SIZES = {"xs": 13, "sm": 15, "md": 17, "lg": 20, "xl": 24, "2xl": 34, "3xl": 44}


def icon(name: str, size: str | int = "sm", cls: str = "") -> Markup:
    """Hasilkan SVG inline untuk ikon `name`.

    `size` menerima kunci baku ("xs".."3xl") atau angka piksel langsung.
    Nama yang tidak dikenal menghasilkan string kosong agar halaman tetap utuh.
    """
    body = _PATHS.get(name)
    if body is None:
        return Markup("")

    px = _SIZES.get(size, size) if isinstance(size, str) else size
    classes = f"icon {cls}".strip()
    return Markup(
        f'<svg class="{classes}" width="{px}" height="{px}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )


def icon_names() -> list[str]:
    return sorted(_PATHS)
