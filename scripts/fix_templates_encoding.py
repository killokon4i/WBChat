# -*- coding: utf-8 -*-
"""Fix templates: legacy cp1251 bytes -> utf-8; utf-8 mojibake line-by-line via cp1251 round-trip."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def decode_raw(data: bytes) -> tuple[str, str]:
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1251"), "cp1251-bytes"


def fix_line(line: str) -> str:
    try:
        return line.encode("cp1251").decode("utf-8")
    except UnicodeError:
        return line


def process_content(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    out = []
    changed = False
    for line in lines:
        if not line:
            out.append(line)
            continue
        # preserve line ending
        core = line.rstrip("\r\n")
        end = line[len(core) :]
        new_core = fix_line(core)
        if new_core != core:
            changed = True
        out.append(new_core + end)
    return "".join(out), changed


def main():
    changed_files = []
    for path in sorted((ROOT / "templates").rglob("*.html")):
        raw = path.read_bytes()
        text, mode = decode_raw(raw)
        fixed, line_changed = process_content(text)
        if mode == "cp1251-bytes":
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed_files.append((path.relative_to(ROOT), "reencoded-" + mode))
        elif fixed != text:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed_files.append((path.relative_to(ROOT), "mojibake-lines"))
    for p, m in changed_files:
        print("updated:", p, m)
    print("count:", len(changed_files))


if __name__ == "__main__":
    main()
