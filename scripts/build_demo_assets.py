#!/usr/bin/env python3
"""Sinkronkan aset demo GitHub Pages dengan aplikasi.

Demo statis memakai design system dan ikon yang sama persis dengan aplikasi,
sehingga apa yang disetujui di demo benar-benar mencerminkan versi produksi:

    docs/assets/style.css  <- app/static/css/style.css   (disalin apa adanya)
    docs/assets/icons.js   <- app/icons.py               (dibangkitkan)

Gaya khusus demo tinggal di docs/assets/demo.css dan tidak pernah tersentuh.

    python scripts/build_demo_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.icons import _PATHS, _SIZES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "icons.js"
CSS_SRC = ROOT / "app" / "static" / "css" / "style.css"
CSS_DST = ROOT / "docs" / "assets" / "style.css"

TEMPLATE = """/* Dibangkitkan oleh scripts/build_demo_icons.py — jangan disunting manual.
   Sumber: app/icons.py */
(function (global) {
  "use strict";

  var PATHS = %(paths)s;
  var SIZES = %(sizes)s;

  /* Hasilkan SVG inline; nama tak dikenal menghasilkan string kosong. */
  function ICON(name, size, cls) {
    var body = PATHS[name];
    if (!body) return "";
    var px = SIZES[size || "sm"] || size || SIZES.sm;
    return '<svg class="icon' + (cls ? " " + cls : "") + '" width="' + px +
      '" height="' + px + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" ' +
      'aria-hidden="true" focusable="false">' + body + '</svg>';
  }

  global.ICON = ICON;
})(window);
"""


def main() -> int:
    js = TEMPLATE % {
        "paths": json.dumps(_PATHS, indent=2, ensure_ascii=False),
        "sizes": json.dumps(_SIZES, ensure_ascii=False),
    }
    OUT.write_text(js, encoding="utf-8")
    print(f"  icons.js  — {len(_PATHS)} ikon, {len(js):,} byte")

    css = CSS_SRC.read_text(encoding="utf-8")
    CSS_DST.write_text(css, encoding="utf-8")
    print(f"  style.css — disalin dari aplikasi, {len(css):,} byte")
    print("Aset demo tersinkron. Gaya khusus demo tetap di docs/assets/demo.css.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
