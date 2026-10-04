"""Builds the SAS Tutors logo as outlined SVG (no font dependency).

Monogram: two Bricolage Grotesque S's around a custom A whose crossbar is a highlighter stroke.
Outputs assets/logo/*.svg (both palettes) and _logo/inline.json (class-based snippets index.html embeds,
so the inline logo follows the page's theme tokens).
    python build.py   (needs: pip install fonttools; fonts are fetched from Google Fonts' GitHub)
"""
import json, os, urllib.request
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.varLib.instancer import instantiateVariableFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "logo")
FONTS = {
    "brico": ("https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
              {"wght": 800, "opsz": 96, "wdth": 100}),
    "fig": ("https://raw.githubusercontent.com/google/fonts/main/ofl/figtree/Figtree%5Bwght%5D.ttf", {"wght": 600}),
}
PALETTES = {  # same tokens as the site: --ink, --blue, --sun, --ink-2, --line
    "v1": dict(ink="#10213A", a="#2D5BE3", hl="#FFD23F", tag="#4A576C", rule="#C9D3E6"),
    "v2": dict(ink="#0F3D3E", a="#5B6B32", hl="#CBD69E", tag="#4E5F5C", rule="#BFD8D2"),
}


def font(name):
    path = os.path.join(HERE, f".{name}.ttf")
    if not os.path.exists(path):
        url, axes = FONTS[name]
        tmp = path + ".var"
        urllib.request.urlretrieve(url, tmp)
        f = TTFont(tmp)
        instantiateVariableFont(f, axes, inplace=True)
        f.save(path)
        os.remove(tmp)
    return TTFont(path)


class Text:
    def __init__(self, f):
        self.f, self.gs, self.cmap, self.hmtx = f, f.getGlyphSet(), f.getBestCmap(), f["hmtx"]

    def width(self, s, track=0):
        return sum(self.hmtx[self.cmap[ord(c)]][0] for c in s) + track * (len(s) - 1)

    def paths(self, s, x, base, scale, track=0, cls="lg-s"):
        out = []
        for c in s:
            g = self.cmap[ord(c)]
            pen = SVGPathPen(self.gs)
            self.gs[g].draw(pen)
            if pen.getCommands():
                out.append(f'<path class="{cls}" transform="translate({x:.1f} {base:.1f}) scale({scale:.4f} {-scale:.4f})" d="{pen.getCommands()}"/>')
            x += (self.hmtx[g][0] + track) * scale
        return out


def monogram(B, x0, base, cap):
    """S A S. Returns (elements, width). cap = cap height in output units."""
    s = cap / 660  # Bricolage cap height is 660/1000
    sw = B.hmtx[B.cmap[ord("S")]][0] * s
    wa, a, t = 0.98 * cap, 0.06 * cap, 0.255 * cap  # A width, half apex, horizontal leg thickness
    gap = 0.055 * cap
    xa = x0 + sw + gap
    cx, top = xa + wa / 2, base - cap
    slope = (wa / 2 - a) / cap
    inner = base - (wa / 2 - t) / slope  # where the inner leg edges meet
    chevron = (f'<path class="lg-a" d="M{xa:.1f} {base:.1f}L{cx - a:.1f} {top:.1f}H{cx + a:.1f}L{xa + wa:.1f} {base:.1f}'
               f'H{xa + wa - t:.1f}L{cx:.1f} {inner:.1f}L{xa + t:.1f} {base:.1f}Z"/>')
    # highlighter crossbar: a rising stroke behind the A
    y1, y2 = base - 0.30 * cap, base - 0.40 * cap
    hl = (f'<path class="lg-hl" pathLength="1" fill="none" stroke-width="{0.17 * cap:.1f}" stroke-linecap="round" '
          f'd="M{xa + 0.17 * cap:.1f} {y1:.1f}Q{cx:.1f} {(y1 + y2) / 2 + 0.03 * cap:.1f} {xa + wa - 0.17 * cap:.1f} {y2:.1f}"/>')
    els = [hl] + B.paths("S", x0, base, s) + [chevron] + B.paths("S", xa + wa + gap, base, s)
    return els, sw * 2 + wa + gap * 2


def stacked(B, F):
    W, pad, cap = 1000, 90, 300
    mono, mw = monogram(B, 0, 0, cap)
    k = (W - 2 * pad) / mw  # scale monogram to the content width
    cap *= k
    mono, mw = monogram(B, pad, pad + cap, cap)
    els = ['<g class="lg-mono">'] + mono + ['</g><g class="lg-word">']
    # TUTORS, tracked, same width as the monogram
    tr = 90
    ts = mw / B.width("TUTORS", tr)
    tcap = 660 * ts
    tb = pad + cap + 0.20 * cap + tcap
    els += B.paths("TUTORS", pad, tb, ts, tr) + ['</g><g class="lg-line">']
    # tagline with rules either side
    words, tr2 = ["LEARN", "GROW", "SUCCEED"], 180
    fs = 0.22 * tcap / 700  # tagline cap height = 22% of TUTORS
    dotgap = 700 * fs * 1.1  # space either side of each separator dot
    widths = [F.width(w, tr2) * fs for w in words]
    total = sum(widths) + 2 * (2 * dotgap)
    yb = tb + 0.42 * tcap + 700 * fs
    x = pad + (mw - total) / 2
    for i, w in enumerate(words):
        els += F.paths(w, x, yb, fs, tr2, cls="lg-tag")
        x += widths[i]
        if i < 2:
            els.append(f'<circle class="lg-a" cx="{x + dotgap:.1f}" cy="{yb - 350 * fs:.1f}" r="{95 * fs:.1f}"/>')
            x += 2 * dotgap
    rule_y = yb - 350 * fs
    lx = pad + (mw - total) / 2
    els += [f'<path class="lg-rule" fill="none" stroke-width="{55 * fs:.1f}" stroke-linecap="round" d="M{pad:.1f} {rule_y:.1f}H{lx - dotgap:.1f}M{lx + total + dotgap:.1f} {rule_y:.1f}H{pad + mw:.1f}"/>']
    els.append("</g>")
    H = yb + pad
    return els, W, H


def horizontal(B):
    cap = 300
    mono, mw = monogram(B, 0, cap, cap)
    gap = 0.16 * cap
    ts = (cap * 0.46) / 660
    tw = B.width("TUTORS", 60) * ts
    tb = cap / 2 + 330 * ts  # vertically centred
    els = mono + B.paths("TUTORS", mw + gap, tb, ts, 60)
    return els, mw + gap + tw, cap


def mark(B):
    """Favicon / app icon: the A on an ink tile."""
    S = 512
    cap = 300
    s = cap / 660
    wa, a, t = 0.98 * cap, 0.06 * cap, 0.255 * cap
    xa, base = (S - wa) / 2, (S + cap) / 2
    cx, top = xa + wa / 2, base - cap
    slope = (wa / 2 - a) / cap
    inner = base - (wa / 2 - t) / slope
    y1, y2 = base - 0.30 * cap, base - 0.40 * cap
    els = [f'<rect class="lg-tile" width="{S}" height="{S}" rx="112"/>',
           f'<path class="lg-hl" pathLength="1" fill="none" stroke-width="{0.17 * cap:.1f}" stroke-linecap="round" d="M{xa + 0.17 * cap:.1f} {y1:.1f}Q{cx:.1f} {(y1 + y2) / 2 + 0.03 * cap:.1f} {xa + wa - 0.17 * cap:.1f} {y2:.1f}"/>',
           f'<path class="lg-mark" d="M{xa:.1f} {base:.1f}L{cx - a:.1f} {top:.1f}H{cx + a:.1f}L{xa + wa:.1f} {base:.1f}H{xa + wa - t:.1f}L{cx:.1f} {inner:.1f}L{xa + t:.1f} {base:.1f}Z"/>']
    return els, S, S


def style(p):
    return (f"<style>.lg-s{{fill:{p['ink']}}}.lg-a{{fill:{p['a']}}}.lg-hl{{stroke:{p['hl']}}}.lg-tag{{fill:{p['tag']}}}"
            f".lg-rule{{stroke:{p['rule']}}}.lg-tile{{fill:{p['ink']}}}.lg-mark{{fill:#fff}}</style>")


def svg(els, w, h, title, css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{title}">'
            f"<title>{title}</title>{css}{''.join(els)}</svg>\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    B, F = Text(font("brico")), Text(font("fig"))
    parts = {"stacked": stacked(B, F), "horizontal": horizontal(B), "mark": mark(B)}
    for v, p in PALETTES.items():
        sfx = "" if v == "v1" else "-v2"
        for name, (els, w, h) in parts.items():
            with open(os.path.join(OUT, f"sas-{name}{sfx}.svg"), "w") as fh:
                fh.write(svg(els, w, h, "SAS Tutors · Learn, Grow, Succeed", style(p)))
    with open(os.path.join(HERE, "inline.json"), "w") as fh:
        json.dump({k: {"viewBox": f"0 0 {w:.0f} {h:.0f}", "body": "".join(e)} for k, (e, w, h) in parts.items()}, fh)
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
