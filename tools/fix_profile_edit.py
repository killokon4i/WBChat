from pathlib import Path

p = Path(__file__).resolve().parents[1] / "templates/accounts/profile_edit.html"
t = p.read_text(encoding="utf-8")

t = t.replace(
    '                <img src="" alt="" class="pe-avatar-preview" id="avatar-preview-new" hidden>\n',
    "",
)

if "pe-avatar-slot" not in t:
    old = """            <div class="pe-avatar-row">
                {% if user.avatar %}
                <img src="{{ user.avatar.url }}" alt="" class="pe-avatar-preview" id="avatar-preview">
                {% else %}
                <div class="pe-avatar-preview" id="avatar-placeholder">{{ user.username|slice:":1"|upper }}</motion>
                {% endif %}
                <div class="pe-avatar-col">"""
    new = """            <div class="pe-avatar-row">
                <div class="pe-avatar-slot" id="avatar-slot">
                {% if user.avatar %}
                <img src="{{ user.avatar.url }}" alt="" class="pe-avatar-preview" id="avatar-preview">
                {% else %}
                <div class="pe-avatar-preview" id="avatar-placeholder">{{ user.username|slice:":1"|upper }}</div>
                {% endif %}
                </div>
                <div class="pe-avatar-col">"""
    old = old.replace("</motion>", "</div>")
    if old not in t:
        old2 = old.replace("</motion>", "</div>")
        if old2 in t:
            t = t.replace(old2, new)
        else:
            # try without typo
            old = """            <div class="pe-avatar-row">
                {% if user.avatar %}
                <img src="{{ user.avatar.url }}" alt="" class="pe-avatar-preview" id="avatar-preview">
                {% else %}
                <div class="pe-avatar-preview" id="avatar-placeholder">{{ user.username|slice:":1"|upper }}</div>
                {% endif %}
                <div class="pe-avatar-col">"""
            t = t.replace(old, new)
    else:
        t = t.replace(old, new)

while "<motion" in t:
    t = t.replace("<motion", "<motion", 1)
while "<motion" in t:
    t = t.replace("<motion", "<div", 1)
while "</motion>" in t:
    t = t.replace("</motion>", "</div>", 1)

t = t.replace("createElement('motion')", "createElement('div')")

# fix script if old version
if "avatar-preview-new" in t:
    raise SystemExit("avatar-preview-new still present")
if "motion" in t:
    raise SystemExit("motion:\n" + "\n".join(l for l in t.splitlines() if "motion" in l))

p.write_text(t, encoding='utf-8')
print("ok")
