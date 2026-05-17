# -*- coding: utf-8 -*-
"""Collapse broken <head>: keep portal.css line, replace everything until </head> before <body>."""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "templates" / "base.html"
t = BASE.read_text(encoding="utf-8")

portal = "{% static 'css/wb-bank-portal.css' %}"
pi = t.index(portal)
gt = t.index(">", pi) + 1
# consume trailing whitespace/newlines after the portal link tag
i0 = gt
while i0 < len(t) and t[i0] in "\r\n \t":
    i0 += 1

body_i = t.index("<body", i0)
head_close = t.rfind("</head>", i0, body_i)
if head_close < 0:
    raise SystemExit("no </head> before <body>")
i1 = head_close

insert = (
    "    <link rel=\"stylesheet\" href=\"{% static 'css/wb-portal-skin.css' %}\">\n"
    "    <link rel=\"stylesheet\" href=\"{% static 'css/wb-marketing-public.css' %}\">\n"
    "    {% block extra_styles %}{% endblock %}\n"
)

t2 = t[:i0] + insert + t[i1:]
if t2.count("{% block extra_styles %}") != 1:
    raise SystemExit(f"extra_styles blocks: {t2.count('{% block extra_styles %}')}")

BASE.write_text(t2, encoding="utf-8", newline="\n")
print("OK", BASE.stat().st_size)
