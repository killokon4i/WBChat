"""Единый SVG path для «хаб» из контуров WBSans.woff2 (как векторное «банк» на wb-bank.ru)."""
import re
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

FONT = "static/fonts/WBSans.woff2"
GLYPHS = ["uni0445", "uni0430", "uni0431"]  # х а б


def main() -> None:
    font = TTFont(FONT)
    gs = font.getGlyphSet()
    hmtx = font["hmtx"].metrics

    # ширина слова в юнитах шрифта (~как у «банк» в их лого viewBox ≈ 88 по X)
    bp = BoundsPen(gs)
    x_accum = 0
    for g in GLYPHS:
        tp = TransformPen(bp, (1, 0, 0, 1, x_accum, 0))
        gs[g].draw(tp)
        x_accum += hmtx[g][0]
    assert bp.bounds
    x_min, y_min, x_max, y_max = bp.bounds
    w = x_max - x_min
    h = y_max - y_min

    target_w = 88.0
    target_h = 30.0  # вписать в высоту строки 44
    scale = min(target_w / w, target_h / h)

    tx = 78.0 - x_min * scale
    # верх контура ≈ 8, центр по вертикали как у шапки
    ty = 8.0 + y_max * scale

    parts: list[str] = []
    x_off = 0
    for g in GLYPHS:
        pen = SVGPathPen(gs)
        tpen = TransformPen(
            pen,
            (scale, 0, 0, -scale, tx + x_off * scale, ty),
        )
        gs[g].draw(tpen)
        cmd = pen.getCommands()
        if cmd:
            parts.append(cmd)
        x_off += hmtx[g][0]

    d = " ".join(parts)

    def rnd_path(s: str) -> str:
        def repl(m: re.Match[str]) -> str:
            v = float(m.group(0))
            r = round(v, 3)
            if r == int(r):
                return str(int(r))
            t = format(r, ".3f").rstrip("0").rstrip(".")
            return t

        return re.sub(r"-?\d+\.\d+(?:e[+-]\d+)?", repl, s)

    print(rnd_path(d))


if __name__ == "__main__":
    main()
