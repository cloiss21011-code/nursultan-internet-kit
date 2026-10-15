#!/usr/bin/env python3
"""Сборка docs/llms-full.txt из страниц документации в порядке nav."""

from pathlib import Path
import sys

DOCS = Path(__file__).resolve().parent.parent / "docs"
ORDER = [
    "index.md",
    "install.md",
    "protocol.md",
    "api.md",
    "examples.md",
    "architecture.md",
    "security.md",
    "ai-rules.md",
    "recipes.md",
    "troubleshooting.md",
    "faq.md",
    "changelog.md",
    "sitemap.md",
]
BANNER = "Nursultan Internet Kit — полный корпус документации (proto 1).\n" \
         "Оригинальный API скриптов Nursultan: https://docs.nursultan.fun/\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parts = [BANNER]
    for name in ORDER:
        path = DOCS / name
        if not path.exists():
            raise SystemExit(f"нет файла: {path}")
        parts.append(f"\n{'=' * 72}\n# {name}\n{'=' * 72}\n")
        parts.append(path.read_text(encoding="utf-8"))
    out = DOCS / "llms-full.txt"
    out.write_text("".join(parts), encoding="utf-8")
    print(f"{out} — {out.stat().st_size} байт, страниц: {len(ORDER)}")


if __name__ == "__main__":
    main()
