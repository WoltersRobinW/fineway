"""fineway wordmark generator: static + animated SVG (SMIL), built from strokes."""
import sys

S = 28          # main stroke
SB = 20         # e bar stroke
H = S / 2
ASC, DESC = -44, 144
G = 14          # gap between letters (outer edges)

MIST, ROSE, DEEP, WINE = "#EEF2F1", "#DA7B93", "#1C3334", "#2E151B"

# letter outer widths and stroke-x anchors
EW = 10         # base width extension of e and a (wide grotesk feel)
W = {"f": 26+34, "i": S, "n": 72+S, "e": 76+EW+S, "w": 100+S, "a": 76+EW+S, "y": 72+S}
GAP_AFTER = {"f": 22}
order = "fineway"
left = {}
x = 0
for ch in order:
    left[ch] = x
    x += W[ch] + GAP_AFTER.get(ch, G)
TOTAL = x - G


def f_paths(asc):
    fx = left["f"] + 26
    R = 20
    top = asc + H  # centerline of hook top
    return [
        f"M{fx} 100V{top+R}A{R} {R} 0 0 1 {fx+R} {top}H{fx+34}",
        f"M{fx-26} {H}H{fx+34}",
    ]


def i_paths(bottom):
    ix = left["i"] + H
    return [f"M{ix} 0V{bottom}", f"M{ix-H} {ASC+H}H{ix+H}"]  # tittle drawn as a short thick line


def n_paths():
    nx = left["n"] + H
    return [f"M{nx} 0V100", f"M{nx} 100V{H+36}A36 36 0 0 1 {nx+72} {H+36}V100"]


def e_paths(extra):
    r = 38
    cr = left["e"] + H + r + EW     # right arc centre stays put
    cl = cr - EW - extra                 # left arc centre moves left when stretched
    c = 0.7071
    ring = (f"M{cr+r} 50A{r} {r} 0 0 0 {cr} {50-r}H{cl}A{r} {r} 0 0 0 {cl-r} 50"
            f"A{r} {r} 0 0 0 {cl} {50+r}H{cr}A{r} {r} 0 0 0 {cr+r*c:.2f} {50+r*c:.2f}")
    bar = f"M{cl-r} 50H{cr+r+H}"
    return [ring], [bar]


def w_paths():
    wx = left["w"] + H
    return [f"M{wx} 0V{100-H-25}A25 25 0 0 0 {wx+50} {100-H-25}V0", f"M{wx+50} {100-H-25}A25 25 0 0 0 {wx+100} {100-H-25}V0"]


def a_paths():
    r = 38
    al = left["a"] + H + r
    ar = al + EW
    return [f"M{ar} {50-r}H{al}A{r} {r} 0 0 0 {al} {50+r}H{ar}A{r} {r} 0 0 0 {ar} {50-r}Z", f"M{ar+r} 0V100"]


def y_paths(desc):
    yx = left["y"] + H
    R2 = 22
    bot = desc - H
    return [f"M{yx} 0V{100-H-36}A36 36 0 0 0 {yx+72} {100-H-36}",
            f"M{yx+72} 0V{bot-R2}A{R2} {R2} 0 0 1 {yx+72-R2} {bot}H{yx+8}"]


BASE = dict(asc=ASC, ibot=100, eext=0, desc=DESC)
STRETCH = dict(asc=-330, ibot=330, eext=420, desc=330)


def letters(st):
    er, eb = e_paths(st["eext"])
    return {
        "f": f_paths(st["asc"]), "i": i_paths(st["ibot"]), "n": n_paths(),
        "e": er, "ebar": eb, "w": w_paths(), "a": a_paths(), "y": y_paths(st["desc"]),
    }


def stroke(d, w=S, color=None):
    c = f' stroke="{color}"' if color else ""
    return f'<path d="{d}" stroke-width="{w}"{c}/>'


# ---------- static ----------
def static_svg(fg, dot, bg=None, pad=36):
    L = letters(BASE)
    x0, y0 = -pad, ASC - pad
    w, h = TOTAL + 2 * pad, (DESC - ASC) + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" width="{w}" height="{h}" role="img" aria-label="fineway">']
    if bg:
        out.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{bg}"/>')
    out.append(f'<g fill="none" stroke="{fg}" stroke-linecap="butt" stroke-linejoin="round">')
    for k in ["f", "n", "e", "w", "a", "y"]:
        for d in L[k]:
            out.append(stroke(d))
    for d in L["ebar"]:
        out.append(stroke(d, SB))
    out.append(stroke(L["i"][0]))
    out.append(stroke(L["i"][1], S, dot))
    out.append("</g></svg>")
    return "\n".join(out)


# ---------- animated ----------
DUR = 3.6
BUILD = 0.60   # stretched -> settled
SPL_FAST = "0.16 1 0.3 1"


def anim_d(d_base, d_str):
    kt = [0, BUILD / DUR, 1]
    vals = ";".join([d_str, d_base, d_base])
    ks = SPL_FAST + ";0 0 1 1"
    return (f'<animate attributeName="d" dur="{DUR}s" repeatCount="1" fill="freeze" calcMode="spline" '
            f'keyTimes="{";".join(f"{t:.4f}" for t in kt)}" keySplines="{ks}" values="{vals}"/>')


def disc(attr, pairs):
    kt = ";".join(f"{t/DUR:.4f}" for t, _ in pairs)
    vals = ";".join(str(v) for _, v in pairs)
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="1" fill="freeze" calcMode="discrete" keyTimes="{kt}" values="{vals}"/>'


def animated_svg(fg=MIST, dot=ROSE, bg=DEEP, vw=1200, vh=675, frame=None, erode=1.6, size=None):
    B, T = letters(BASE), letters(STRETCH)
    cx = TOTAL / 2
    cy = 50
    x0, y0 = cx - vw / 2, cy - vh / 2
    if frame:
        x0, y0, vw, vh = frame
    sw, sh = size or (vw, vh)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{x0} {y0} {vw} {vh}" width="{sw}" height="{sh}" role="img" aria-label="fineway">',
           f'<defs><filter id="ol" filterUnits="userSpaceOnUse" x="{x0}" y="{y0}" width="{vw}" height="{vh}">'
           f'<feMorphology in="SourceGraphic" operator="erode" radius="{erode}" result="e"/>'
           '<feComposite in="SourceGraphic" in2="e" operator="out"/></filter>',
           f'<g id="word" fill="none" stroke="{fg}" stroke-linecap="butt" stroke-linejoin="round">']

    # letter-by-letter dissolve times (outline phase)
    off = {ch: 2.15 + k * 0.05 for k, ch in enumerate(order)}

    def letter_group(ch, keys, extra_tf=None):
        g = ['<g>']
        if extra_tf:
            g.append(extra_tf)
        for key, width, color in keys:
            for db, dt in zip(B[key], T[key]):
                c = f' stroke="{color}"' if color else ""
                if db == dt:
                    g.append(f'<path d="{db}" stroke-width="{width}"{c}/>')
                else:
                    g.append(f'<path d="{db}" stroke-width="{width}"{c}>{anim_d(db, dt)}</path>')
        g.append("</g>")
        return "".join(g)

    # f, i, n slide in from the left with the stretched e
    shift = STRETCH["eext"]
    tf = (f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="1" fill="freeze" '
          f'calcMode="spline" keyTimes="0;{BUILD/DUR:.4f};1" '
          f'keySplines="{SPL_FAST};0 0 1 1" values="-{shift} 0;0 0;0 0"/>')
    out.append(f'<g>{tf}')
    out.append(letter_group("f", [("f", S, None)]))
    # i: stem + rose tittle
    out.append(f'<g>'
               f'<path d="{B["i"][0]}" stroke-width="{S}">{anim_d(B["i"][0], T["i"][0])}</path>'
               f'<path d="{B["i"][1]}" stroke-width="{S}" stroke="{dot}"/></g>')
    out.append(letter_group("n", [("n", S, None)]))
    out.append("</g>")
    out.append(letter_group("e", [("e", S, None), ("ebar", SB, None)]))
    out.append(letter_group("w", [("w", S, None)]))
    out.append(letter_group("a", [("a", S, None)]))
    out.append(letter_group("y", [("y", S, None)]))
    out.append("</g></defs>")

    if bg:
        out.append(f'<rect x="{x0}" y="{y0}" width="{vw}" height="{vh}" fill="{bg}"/>')
    solid = disc("opacity", [(0,1),(1.80,0),(1.90,1),(2.00,0),(2.10,1)])
    outl = disc("opacity", [(0,0),(1.80,1),(1.90,0),(2.00,1),(2.10,0)])
    out.append(f'<use href="#word" xlink:href="#word">{solid}</use>')
    out.append(f'<use href="#word" xlink:href="#word" filter="url(#ol)" opacity="0">{outl}</use>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    d = sys.argv[1]
    open(f"{d}/fineway-logo-light.svg", "w").write(static_svg(MIST, ROSE))           # for dark backgrounds
    open(f"{d}/fineway-logo-dark.svg", "w").write(static_svg(WINE, ROSE))            # for light backgrounds
    open(f"{d}/fineway-logo-on-green.svg", "w").write(static_svg(MIST, ROSE, DEEP))
    open(f"{d}/fineway-logo-on-rose.svg", "w").write(static_svg(WINE, MIST, ROSE))
    open(f"{d}/fineway-logo-animated.svg", "w").write(animated_svg())
    # website header: transparent, cropped to the wordmark, outline thick enough at ~40px tall
    fr = (-24, ASC - 16, TOTAL + 48, (DESC - ASC) + 32)
    open(f"{d}/fineway-logo-animated-transparent.svg", "w").write(
        animated_svg(bg=None, frame=fr, erode=7, size=(round(fr[2]), round(fr[3]))))
    print("total width", TOTAL)
