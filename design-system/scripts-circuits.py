"""Generate the Alpha One Labs PCB-style circuit graphics (assets/circuits/pcb-*.svg).

Rules, like a real board: traces run straight or at 45°, buses keep a fixed
pitch, every trace ends in a via (annular ring) or an SMD pad. Everything uses
currentColor so CSS can set the color (brass gold by default).
"""
import math, pathlib

OUT = pathlib.Path(__file__).parent / "assets" / "circuits"
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" color="#D4AF37" fill="none" stroke="currentColor" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'

def via(x, y, r=5.5, w=3):
    return f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" stroke-width="{w:g}"/>'

def pad(x, y, w=10, h=16):
    return f'<rect x="{x - w / 2:g}" y="{y - h / 2:g}" width="{w:g}" height="{h:g}" fill="currentColor" stroke="none"/>'

def poly(points):
    return '<path d="M' + " L".join(f"{x:g} {y:g}" for x, y in points) + '"/>'

def write(name, vb, body, w=3):
    (OUT / name).write_text(HEAD.format(vb=vb, w=w) + "".join(body) + "</svg>\n")
    print("wrote", name)

# 1) Corner bus: 6 traces enter from the left, bend 45° down, end in vias.
def corner():
    body, pitch = [], 16
    for i in range(6):
        y = 24 + i * pitch
        x_bend = 150 - i * pitch           # stagger so the 45° runs stay parallel
        x_down = 250 - i * pitch
        drop = x_down - x_bend
        pts = [(0, y), (x_bend, y), (x_bend + drop * 0.35, y + drop * 0.35), (x_down - 10, y + drop * 0.35), (x_down, y + drop * 0.35 + 10), (x_down, 230 + i * 6)]
        body.append(poly(pts))
        body.append(via(x_down, 230 + i * 6 + 9))
    write("pcb-corner.svg", "0 0 300 300", body)

# 2) Divider: a 4-trace bus lands on the left pins of an SOIC-style chip; the
#    right pins fan out at 45° to staggered vias. One 16px pitch throughout.
def divider():
    body, pitch = [], 16
    pins = [34 + i * pitch for i in range(4)]          # pin rows on the chip
    body.append('<rect x="340" y="20" width="84" height="80" stroke-width="3.5"/>')
    body.append('<circle cx="352" cy="32" r="3.2" fill="currentColor" stroke="none"/>')
    for i, y in enumerate(pins):
        body.append(pad(333, y, 14, 6)); body.append(pad(431, y, 14, 6))
        # left: run in high, drop one pitch at 45°, land on the pad
        y_in = y - pitch
        body.append(poly([(0, y_in), (196 + i * 6, y_in), (196 + i * 6 + pitch, y), (326, y)]))
        # right: leave the pad, rise one pitch at 45°, run out, drop 45° into a via
        x_rise = 456 + i * 6
        x_end = 690 - i * 22
        body.append(poly([(438, y), (x_rise, y), (x_rise + pitch, y - pitch), (x_end, y - pitch), (x_end + 14, y - pitch + 14)]))
        body.append(via(x_end + 18, y - pitch + 18))
    write("pcb-divider.svg", "0 0 760 120", body)

# 3) Chip: QFP-32 with pin-1 dot, pins on four sides, traces fanning out at 45° to vias.
def chip():
    body = []
    cx, cy, s = 240, 170, 110
    x0, y0 = cx - s / 2, cy - s / 2
    body.append(f'<rect x="{x0:g}" y="{y0:g}" width="{s:g}" height="{s:g}" stroke-width="4"/>')
    body.append(f'<circle cx="{x0 + 14:g}" cy="{y0 + 14:g}" r="4" fill="currentColor" stroke="none"/>')
    n, pitch = 8, 12
    for i in range(n):
        off = (i - (n - 1) / 2) * pitch          # offset from the chip's center line
        px, py = cx + off, cy + off
        body.append(pad(px, y0 - 8, 6, 12)); body.append(pad(px, y0 + s + 8, 6, 12))
        body.append(pad(x0 - 8, py, 12, 6)); body.append(pad(x0 + s + 8, py, 12, 6))
        fan = abs(off) * 1.3
        sgn = 1 if off >= 0 else -1
        if i % 2 == 0:   # top and bottom: out, 45° spread, out to a via
            for side in (-1, 1):
                ys = (y0 - 14) if side < 0 else (y0 + s + 14)
                yb = ys + side * 12
                pts = [(px, ys), (px, yb), (px + sgn * fan, yb + side * fan), (px + sgn * fan, yb + side * (fan + 16))]
                body.append(poly(pts)); body.append(via(pts[-1][0], pts[-1][1] + side * 7, 4.5, 2.5))
        else:            # left and right
            for side in (-1, 1):
                xs = (x0 - 14) if side < 0 else (x0 + s + 14)
                xb = xs + side * 12
                pts = [(xs, py), (xb, py), (xb + side * fan, py + sgn * fan), (xb + side * (fan + 34), py + sgn * fan)]
                body.append(poly(pts)); body.append(via(pts[-1][0] + side * 7, pts[-1][1], 4.5, 2.5))
    write("pcb-chip.svg", "0 0 480 340", body, w=2.5)

# 4) Frame: hero framing traces that wrap a corner with a header connector.
def frame():
    body, pitch = [], 14
    for i in range(5):
        x = 30 + i * pitch
        y_turn = 200 - i * pitch
        pts = [(x, 420), (x, y_turn), (x + 60, y_turn - 60), (360 - i * 10, y_turn - 60)]
        body.append(poly(pts)); body.append(via(pts[-1][0] + 8, pts[-1][1]))
    # 2x4 pin header
    for r in range(2):
        for c in range(4):
            body.append(f'<rect x="{150 + c * 20:g}" y="{330 + r * 20:g}" width="14" height="14" stroke-width="2.5"/>')
            body.append(f'<circle cx="{157 + c * 20:g}" cy="{337 + r * 20:g}" r="3" fill="currentColor" stroke="none"/>')
    write("pcb-frame.svg", "0 0 420 420", body)

corner(); divider(); chip(); frame()

# 5) Ring traces: three traces with 45° bends, open ring terminals at both ends.
def traces():
    body = []
    routes = [
        [(14, 70), (60, 24), (150, 24), (176, 50), (176, 106)],
        [(14, 104), (46, 104), (96, 54), (128, 54), (150, 76), (150, 142)],
        [(14, 140), (96, 140), (124, 112), (124, 84)],
    ]
    for r in routes:
        a, b = r[0], r[-1]
        body.append(poly([(a[0] + 7, a[1])] + r[1:-1] + [(b[0], b[1] - 7 if b[1] > r[-2][1] else b[1] + 7)]))
        body.append(via(a[0], a[1], 6, 3)); body.append(via(b[0], b[1], 6, 3))
    write("pcb-traces.svg", "0 0 200 160", body)

# 6) Chip icon: package with pins on four sides and an inner die outline.
def chip_icon():
    body = ['<rect x="22" y="22" width="56" height="56" stroke-width="4"/>', '<rect x="36" y="36" width="28" height="28" stroke-width="2.5"/>']
    for i in range(4):
        o = 32 + i * 12
        body.append(poly([(o, 8), (o, 22)])); body.append(poly([(o, 78), (o, 92)]))
        body.append(poly([(8, o), (22, o)])); body.append(poly([(78, o), (92, o)]))
    write("pcb-chip-icon.svg", "0 0 100 100", body, w=4)

# 7) Hazard bars: an outlined bar with diagonal stripes, and a solid slanted stripe row.
def hatch():
    body = ['<path d="M18 10 H150 L132 40 H0 Z" stroke-width="3"/>']
    for x in range(14, 150, 14):
        body.append(f'<path d="M{x + 4:g} 13 L{x - 10:g} 37" stroke-width="5" stroke-linecap="butt"/>')
    for i in range(6):
        x = 190 + i * 22
        body.append(f'<path d="M{x + 16:g} 10 H{x + 28:g} L{x + 10:g} 40 H{x - 2:g} Z" fill="currentColor" stroke="none"/>')
    write("pcb-hatch.svg", "0 0 340 50", body)

# 8) Bracket frame: double-line frame with 45° cut corners, open on the right.
def bracket():
    body = []
    for k, inset in enumerate((0, 12)):
        x0, y0, x1, y1 = 10 + inset, 10 + inset, 390 - inset, 110 - inset
        c = 18
        body.append(poly([(x1, y0 + 26), (x1, y0), (x0 + c, y0), (x0, y0 + c), (x0, y1)]))
        body.append(poly([(x0 + 40, y1), (x1 - c, y1), (x1, y1 - c), (x1, y1 - 34)]) if k == 0 else poly([(x0 + 20, y1), (x0 + 120, y1)]))
    write("pcb-bracket.svg", "0 0 400 120", body)

traces(); chip_icon(); hatch(); bracket()
