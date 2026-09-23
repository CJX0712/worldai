# Author: 晨星
"""P0 gate: scan the repo for emoji used as functional icons / in code.
Exit 1 on any hit. Emoji are allowed only in UGC, never in UI/source.
Detection is codepoint-range based (no literal emoji in this file)."""
from __future__ import annotations

import sys
from pathlib import Path

EMOJI_RANGES: list[tuple[int, int]] = [
    (0x1F300, 0x1F9FF),  # symbols & pictographs, emoticons, transport, supplemental
    (0x1F000, 0x1F0FF),  # mahjong / domino / playing cards
    (0x1FA00, 0x1FAFF),  # chess, extended-A
    (0x2600, 0x26FF),    # misc symbols
    (0x2700, 0x27BF),    # dingbats
    (0x2190, 0x21FF),    # arrows (often used as icons)
    (0x2B00, 0x2BFF),    # misc symbols and arrows
    (0xFE00, 0xFE0F),    # variation selectors (emoji presentation)
    (0x1F1E6, 0x1F1FF),  # regional indicators
]
EXTRA_CODEPOINTS = {0x200D, 0x20E3, 0x3030, 0x303D}  # ZWJ, keycap, wavy dash

TEXT_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".html", ".css",
    ".md", ".json", ".yaml", ".yml", ".txt", ".toml",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def is_emoji(ch: str) -> bool:
    cp = ord(ch)
    if cp in EXTRA_CODEPOINTS:
        return True
    return any(lo <= cp <= hi for lo, hi in EMOJI_RANGES)


def scan(root: Path) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(is_emoji(ch) for ch in line):
                hits.append((path, lineno, line.strip()[:80]))
    return hits


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits = scan(root)
    if hits:
        print(f"P0 VIOLATION: {len(hits)} emoji occurrence(s) found:")
        for path, lineno, snippet in hits:
            print(f"  {path}:{lineno}: {snippet}")
        return 1
    print("emoji scan: PASS (0 occurrences)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
