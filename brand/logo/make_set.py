"""fineway logo set: rectangle, square, icon; positive and negative; three colourways."""
import importlib.util, os, sys

spec = importlib.util.spec_from_file_location("gen", os.path.join(os.path.dirname(__file__), "gen.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

THEMES = {
    # name: (dark background, light background, ink on light, ink on dark, accent)
    "rose":  ("#1C3334", "#EEF2F1", "#2E151B", "#EEF2F1", "#DA7B93"),
    "blue":  ("#2E4052", "#FFFFFF", "#2E4052", "#FFFFFF", "#FFC857"),
    "olive": ("#283618", "#FEFAE0", "#283618", "#FEFAE0", "#DDA15E"),
}


def paths(fg, dot, only=None):
    """Stroke paths of the settled wordmark (only: subset of letters)."""
    L = g.letters(g.BASE)
    keys = only or ["f", "i", "n", "e", "w", "a", "y"]
    out = [f'<g fill="none" stroke="{fg}" stroke-linecap="butt" stroke-linejoin="round">']
    for k in keys:
        if k == "i":
            out.append(g.stroke(L["i"][0]))
            out.append(g.stroke(L["i"][1], g.S, dot))
            continue
        for d in L[k]:
            out.append(g.stroke(d))
        if k == "e":
            for d in L["ebar"]:
                out.append(g.stroke(d, g.SB))
    out.append("</g>")
    return "".join(out)


def svg(w, h, body, bg=None, label="fineway"):
    r = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">']
    if bg:
        r.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
    r.append(body)
    r.append("</svg>")
    return "\n".join(r)


def placed(fg, dot, box_w, box_h, target_w=None, target_h=None, only=None, x0=None, x1=None, y1=None):
    """Scale and centre glyphs into a box. Glyph bounds in design units."""
    gx0 = x0 if x0 is not None else -0.0
    gx1 = x1 if x1 is not None else g.TOTAL
    gy0, gy1 = g.ASC, (y1 if y1 is not None else g.DESC)
    gw, gh = gx1 - gx0, gy1 - gy0
    s = min(target_w / gw if target_w else 1e9, target_h / gh if target_h else 1e9)
    tx = (box_w - gw * s) / 2 - gx0 * s
    ty = (box_h - gh * s) / 2 - gy0 * s
    return f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{paths(fg, dot, only)}</g>'


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    made = []
    for name, (dark, light, ink_l, ink_d, acc) in THEMES.items():
        d = os.path.join(outdir, name); os.makedirs(d, exist_ok=True)
        modes = {"positive": (light, ink_l), "negative": (dark, ink_d)}
        for mode, (bg, ink) in modes.items():
            # rectangle 3:1, with background and transparent
            W, H = 1800, 600
            body = placed(ink, acc, W, H, target_w=W * 0.70)
            for suffix, b in (("", bg), ("-transparent", None)):
                f = os.path.join(d, f"fineway-{name}-rectangle-{mode}{suffix}.svg")
                open(f, "w").write(svg(W, H, body, b)); made.append(f)
            # square 1:1 wordmark
            W = H = 1080
            body = placed(ink, acc, W, H, target_w=W * 0.70)
            f = os.path.join(d, f"fineway-{name}-square-{mode}.svg"); open(f, "w").write(svg(W, H, body, bg)); made.append(f)
            # icon 1:1: "fi"
            W = H = 1024
            fi_x1 = g.left["i"] + g.S
            body = placed(ink, acc, W, H, target_h=H * 0.50, only=["f", "i"], x0=0, x1=fi_x1, y1=100)
            f = os.path.join(d, f"fineway-{name}-icon-{mode}.svg"); open(f, "w").write(svg(W, H, body, bg, "fineway icon")); made.append(f)
    return made


if __name__ == "__main__":
    for f in build(sys.argv[1]):
        print(f)
