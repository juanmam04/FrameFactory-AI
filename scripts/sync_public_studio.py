"""Copy Studio UI into public/ so Vercel static hosting stays in sync."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pairs = [
    (ROOT / "studio" / "templates" / "index.html", ROOT / "public" / "index.html"),
    (ROOT / "studio" / "static" / "studio.css", ROOT / "public" / "assets" / "studio.css"),
    (ROOT / "studio" / "static" / "studio.js", ROOT / "public" / "assets" / "studio.js"),
    (ROOT / "studio" / "static" / "logo.svg", ROOT / "public" / "assets" / "logo.svg"),
    (ROOT / "studio" / "static" / "logo.png", ROOT / "public" / "assets" / "logo.png"),
    (
        ROOT / "studio" / "static" / "manifest.webmanifest",
        ROOT / "public" / "assets" / "manifest.webmanifest",
    ),
]


def main() -> None:
    for src, dst in pairs:
        if not src.is_file():
            print("skip missing", src)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print("ok", dst.relative_to(ROOT))


if __name__ == "__main__":
    main()
