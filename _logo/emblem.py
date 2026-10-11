"""Builds the emblem (open book, winding path, tree, star, crescent moon) as an inline SVG
snippet for the splash, plus assets/logo/sas-emblem.svg. Coordinates follow the 1254px source art.
    python emblem.py
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
TEAL, OLIVE, LEAF, GOLD = "#1F5552", "#7E9651", "#5E7A3E", "#F2C463"
CX, CY, R = 627, 615, 410  # moon circle


def band(a0, a1, thick, taper_end, n=72):
    """Crescent band between angles a0→a1 (degrees, screen coords), thickness from thick(θ), tapering at the a1 end."""
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        w = thick(a) * (1 - max(0, (t - (1 - taper_end)) / taper_end) * 0.92 if t > 1 - taper_end else 1)
        outer.append((CX + R * math.cos(a), CY + R * math.sin(a)))
        inner.append((CX + (R - w) * math.cos(a), CY + (R - w) * math.sin(a)))
    pts = outer + inner[::-1]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def centerline(a0, a1, inset, n=48):
    pts = [(CX + (R - inset) * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
            CY + (R - inset) * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def leaf(x, y, angle, length, width, fill, i):
    l, w = length, width
    d = f"M0,0 C{w:.0f},{-l*.3:.0f} {w*.6:.0f},{-l*.8:.0f} 0,{-l:.0f} C{-w*.6:.0f},{-l*.8:.0f} {-w:.0f},{-l*.3:.0f} 0,0Z"
    vein = f"M0,{-l*.12:.0f} Q{w*.08:.0f},{-l*.5:.0f} 0,{-l*.86:.0f}"
    return (f'<g class="e-leaf" style="--i:{i}" transform="translate({x} {y}) rotate({angle})">'
            f'<path fill="{fill}" d="{d}"/><path fill="none" stroke="#F6F3E6" stroke-opacity=".55" stroke-width="3" d="{vein}"/></g>')


thick = lambda a: 26 + 44 * (1 - math.cos(a)) / 2   # 70 on the left, 48 across the top, 26 on the right
moon_teal = band(151, 309, thick, 0.25)
moon_olive = band(34, -25, lambda a: 22, 0.4)
book_teal_l = "M200,940 C360,890 548,912 627,1010 L627,1058 C520,986 360,958 200,940Z"
book_olive_l = "M210,905 C300,826 486,812 616,944 C520,900 372,884 210,905Z"
road = ("M612,700 C595,725 556,738 552,758 C548,780 590,792 566,812 C540,834 480,842 455,848 "
        "L627,940 L812,862 C770,842 742,822 724,800 C700,772 660,768 676,746 C690,728 676,716 640,708Z")
stripe = "M642,716 C690,724 664,760 706,786 C740,808 772,838 806,860"
trunk = ("M596,712 C612,676 626,650 616,612 C610,590 618,570 624,552 L634,552 "
         "C640,580 646,612 652,640 C660,676 650,698 668,712Z")
branches = "M626,602 C604,588 584,580 566,575 M634,590 C654,572 672,558 690,546 M630,575 C630,530 628,490 628,462"
leaves = "".join([
    leaf(628, 464, 0, 86, 36, OLIVE, 0),
    leaf(606, 514, -40, 110, 44, TEAL, 1),
    leaf(650, 514, 42, 110, 44, OLIVE, 2),
    leaf(566, 575, -72, 126, 46, OLIVE, 3),
    leaf(690, 548, 70, 126, 46, TEAL, 4),
    leaf(588, 624, -118, 70, 30, OLIVE, 5),
])
star = "M628,290 C632,316 640,326 664,330 C640,334 632,344 628,370 C624,344 616,334 592,330 C616,326 624,316 628,290Z"

svg = f'''<svg class="emblem" viewBox="180 170 894 910" role="img" aria-label="SAS Tutors">
<defs>
<radialGradient id="e-glow" cx="628" cy="330" r="420" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFFBEA"/><stop offset=".55" stop-color="#F6F3E6"/><stop offset="1" stop-color="#EEEBDC"/></radialGradient>
<mask id="e-m1" maskUnits="userSpaceOnUse" x="0" y="0" width="1254" height="1254"><path class="e-sweep" pathLength="1" fill="none" stroke="#fff" stroke-width="160" d="{centerline(151, 309, 35)}"/></mask>
<mask id="e-m2" maskUnits="userSpaceOnUse" x="0" y="0" width="1254" height="1254"><path class="e-sweep" pathLength="1" fill="none" stroke="#fff" stroke-width="90" d="{centerline(34, -25, 11)}"/></mask>
</defs>
<circle class="e-disc" cx="{CX}" cy="{CY}" r="{R-20}" fill="url(#e-glow)"/>
<g class="e-moon"><path mask="url(#e-m1)" fill="{TEAL}" d="{moon_teal}"/><path mask="url(#e-m2)" fill="{OLIVE}" d="{moon_olive}"/></g>
<g class="e-road"><path fill="{TEAL}" d="{road}"/><path fill="none" stroke="{OLIVE}" stroke-width="16" stroke-linecap="round" d="{stripe}"/></g>
<g class="e-book"><path fill="{TEAL}" d="{book_teal_l}"/><path fill="{OLIVE}" d="{book_olive_l}"/>
<g transform="translate(1254 0) scale(-1 1)"><path fill="{TEAL}" d="{book_teal_l}"/><path fill="{OLIVE}" d="{book_olive_l}"/></g></g>
<g class="e-tree"><path fill="{TEAL}" d="{trunk}"/><path fill="none" stroke="{TEAL}" stroke-width="11" stroke-linecap="round" d="{branches}"/>{leaves}</g>
<path class="e-star" fill="{GOLD}" d="{star}"/>
</svg>'''

open(os.path.join(HERE, "emblem.svg.html"), "w").write(svg)
os.makedirs(os.path.join(HERE, "..", "assets", "logo"), exist_ok=True)
open(os.path.join(HERE, "..", "assets", "logo", "sas-emblem.svg"), "w").write(svg.replace('<svg class="emblem"', '<svg xmlns="http://www.w3.org/2000/svg"'))
print(len(svg), "bytes")
