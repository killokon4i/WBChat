"""
«хаб» для лого: «а» и «б» — подпути официального «банк»; «х» — два четырёхугольника
как в разметке M(L,T)M(L+c,T)(R,B)(R-c,B): диагональные полосы с **горизонтальными**
верхом и низом; **X_CAP_FRAC=0.3** (как на референсе: тупик ~30% ширины, зазор ~40%),
масштаб — под **X_STROKE**.

  python scripts/build_hub_logo_hab.py
  python scripts/apply_hub_path.py

  Доля горизонтального «торца» полосы **X_CAP_FRAC** (≈0.3 → зазор между штрихами
  сверху/снизу ≈40% ширины буквы). Масштаб подгоняется под **X_STROKE**.

  Зависимости: pip install svgpathtools shapely
"""
from __future__ import annotations

import math
import re

from shapely.geometry import Polygon
from shapely.ops import unary_union
from svgpathtools import parse_path
from svgpathtools.path import Path as SVGPath

# Третий path «банк» (wb-bank.ru) — только буквы б и а (до н и к не идём).
BANK_D = (
    "M80.88 20.969V12.84c0-5.154 2.814-7.961 7.856-7.961h8.234V3.035h4.747V4.88c0 2.807-1.806 4.818-4.747 4.818h-8.234c-2.185 0-3.067.964-3.067 3.143v4.567c.924-1.969 3.78-4.064 8.066-4.064 "
    "5.462 0 10.293 3.478 10.293 10.224 0 6.662-5.252 11.062-11.385 11.062-6.554 0-11.764-4.106-11.764-13.66m11.763-3.059c-4.117 0-6.176 2.933-6.176 5.866s2.059 5.866 6.176 5.866 "
    "6.176-2.933 6.176-5.866-2.06-5.866-6.176-5.866M128.745 13.092v20.95h-5.042V31.78c-1.974 1.886-4.579 2.85-7.184 2.85-5.167 0-10.377-3.687-10.377-11.062s5.21-11.062 10.377-11.062c2.605 0 5.21.964 7.184 2.85V13.09zm-17.393 10.475c0 3.561 2.521 6.075 6.176 6.075s6.175-2.514 6.175-6.075-2.52-6.076-6.175-6.076-6.176 2.514-6.176 6.076M146.959 34.042v-8.087h-9.831v8.087h-5.042v-20.95h5.042v7.877h9.831V13.09H152v20.951zM155.349 34.042v-20.95h5.041v9.93l8.781-9.93h5.713l-8.822 9.972 9.873 10.978h-6.176l-9.369-10.35v10.35z"
)

# Как у вертикали «а» в банковском path.
X_STROKE = 5.042
# Полуширина / полувысота: 1.0 — квадратный бокс буквы (как в референсе).
X_ASPECT = 1.0
X_INSET = 0.52
X_SHIFT_Y = 0.16
X_SIZE_FRAC = 0.94
# Доля ширины буквы, которую занимает один горизонтальный «тупик» штриха (референс ~0.3 → промежуток 1−2·0.3≈40%).
X_CAP_FRAC = 0.3
# Подтянуть «а»/«б» к «х». На иконке ~36px шаг <1 в viewBox почти не виден — керн 2–4+.
X_HA_TRACK = 3.0


def split_be_a_only(d: str) -> tuple[SVGPath, SVGPath]:
    parts = re.findall(r"M[^M]*", d)
    if len(parts) < 2:
        raise RuntimeError("ожидались минимум 2 буквы в path")
    return parse_path(parts[0].strip()), parse_path(parts[1].strip())


def bbox_x(p: SVGPath) -> tuple[float, float, float, float]:
    mi, ma, mj, mk = p.bbox()
    return mi, ma, mj, mk


def _poly_to_svg_d(poly: object, tol: float = 0.02) -> str:
    """Один внешний контур полигона → path d (ортогональные координаты как в SVG)."""
    g = poly.simplify(tol, preserve_topology=True)
    ring = g.exterior
    xs, ys = ring.coords.xy
    pts = list(zip(xs, ys))[:-1]
    if not pts:
        return ""
    chunks = [f"M{pts[0][0]:.5f},{pts[0][1]:.5f}"]
    for x, y in pts[1:]:
        chunks.append(f"L{x:.5f},{y:.5f}")
    chunks.append("Z")
    return " ".join(chunks)


def _perpendicular_strokeThickness(w_box: float, h_box: float, cap: float) -> float:
    """Толщина полосы (расстояние между длинными параллельными сторонами)."""
    den = math.hypot(w_box - cap, h_box)
    if den < 1e-12:
        return 0.0
    return cap * h_box / den


def path_x_horiz_cap_quads(
    a_top: float,
    a_bottom: float,
    *,
    stroke: float = X_STROKE,
    aspect: float = X_ASPECT,
    inset: float = X_INSET,
    shift_y: float = X_SHIFT_Y,
    size_frac: float = X_SIZE_FRAC,
    cap_frac: float = X_CAP_FRAC,
) -> SVGPath:
    """
    Два четырёхугольника, горизонтальные верх/низ:
      \\: (L,T)-(L+c,T)-(R,B)-(R-c,B)
      /: (R,T)-(R-c,T)-(L,B)-(L+c,B)
    c = cap_frac * ширина бокса (0.3 → ~40% светлого зазора между штрихами).
    Масштаб v_half/h_half подгоняет перпендикулярную толщину к stroke.
    """
    cy = (a_top + a_bottom) * 0.5 + shift_y
    avail = a_bottom - a_top
    v_half = max(0.0, (avail - stroke - 2 * inset) * 0.5) * size_frac
    h_half = v_half * aspect
    cx = 0.0

    w_box = 2.0 * h_half
    h_box = 2.0 * v_half
    cap = cap_frac * w_box
    if cap >= w_box * 0.499:
        cap = w_box * 0.33
    s_geom = _perpendicular_strokeThickness(w_box, h_box, cap)
    if s_geom > 1e-9:
        v_half *= stroke / s_geom
        h_half *= stroke / s_geom

    y_top = cy - v_half
    y_bottom = cy + v_half
    x_left = cx - h_half
    x_right = cx + h_half
    w_box = x_right - x_left
    h_box = y_bottom - y_top
    cap = cap_frac * w_box
    if cap >= w_box * 0.499:
        cap = w_box * 0.33

    lft, rt, tp, bt = x_left, x_right, y_top, y_bottom
    q1 = Polygon([(lft, tp), (lft + cap, tp), (rt, bt), (rt - cap, bt)])
    q2 = Polygon([(rt, tp), (rt - cap, tp), (lft, bt), (lft + cap, bt)])
    u = unary_union([q1, q2])
    if u.is_empty:
        raise RuntimeError("пустая геометрия «х»")
    if u.geom_type == "MultiPolygon":
        u = max(u.geoms, key=lambda g: g.area)
    d = _poly_to_svg_d(u)
    return parse_path(d)


def round_d(p: SVGPath, nd: int = 3) -> str:
    s = p.d()

    def repl(m: re.Match[str]) -> str:
        v = float(m.group(0))
        r = round(v, nd)
        if abs(r - int(r)) < 1e-9:
            return str(int(r))
        t = format(r, f".{nd}f").rstrip("0").rstrip(".")
        return t

    return re.sub(r"-?\d+\.\d+(?:e[+-]\d+)?", repl, s)


def main() -> None:
    be_raw, a_raw = split_be_a_only(BANK_D)

    be_l, be_r, _, _ = bbox_x(be_raw)
    a_l, a_r, a_t, a_b = bbox_x(a_raw)
    gap_ab = a_l - be_r

    anchor_left = 80.88

    h_path = path_x_horiz_cap_quads(a_t, a_b)
    h_l, _, _, _ = bbox_x(h_path)
    h_path = h_path.translated(anchor_left - h_l)

    h_r = bbox_x(h_path)[1]
    a_path = a_raw.translated(h_r + gap_ab - X_HA_TRACK - a_l)

    a_r2 = bbox_x(a_path)[1]
    be_path = be_raw.translated(a_r2 + gap_ab - be_l)

    merged = SVGPath()
    for seg in h_path:
        merged.append(seg)
    for seg in a_path:
        merged.append(seg)
    for seg in be_path:
        merged.append(seg)
    print(round_d(merged, 3))


if __name__ == "__main__":
    main()
