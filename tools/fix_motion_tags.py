from pathlib import Path

p = Path(__file__).resolve().parents[1] / "templates/accounts/profile_edit.html"
t = p.read_text(encoding="utf-8")
while "<motion" in t or "</motion>" in t:
    t = t.replace("<motion", "<div", 1)
    t = t.replace("</motion>", "</div>", 1)
t = t.replace("createElement('div')", "createElement('div')")  # noop
if "motion" in t:
    raise SystemExit("motion remains")
p.write_text(t, encoding="utf-8")
print("ok")
