"""Apply scripts/build_hub_logo_hab.py output into templates (run after editing the script)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    new = subprocess.check_output(
        [sys.executable, str(ROOT / "scripts" / "build_hub_logo_hab.py")],
        text=True,
    ).strip()

    for rel in (
        "templates/partials/wb_bank_logo.html",
        "static/img/wb-bank-logo.svg",
        "logo-preview.html",
    ):
        fp = ROOT / rel
        t = fp.read_text(encoding="utf-8")

        def repl(m: re.Match[str]) -> str:
            old = m.group(2)
            if not old.startswith("M "):
                return m.group(0)
            # Merged «хаб»: вертикаль «а» (34.042) + круг /x-height из банковского path.
            if "34.042" in old and ("12.506" in old or "12.505" in old):
                return f'{m.group(1)}{new}{m.group(3)}'
            return m.group(0)

        t2 = re.sub(
            r'(<path fill="(?:currentColor|#000000)" d=")([^"]+)(")',
            repl,
            t,
        )
        if t2 != t:
            fp.write_text(t2, encoding="utf-8")
            print("patched", rel)


if __name__ == "__main__":
    main()
