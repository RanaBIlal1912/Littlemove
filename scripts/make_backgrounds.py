"""Draw the illustrated page backgrounds used by the site.

    python scripts/make_backgrounds.py static/img/bg

Writes:
  hero.jpg          sunny sky, clouds, bunting, balloons and rolling hills (2000x900)
  footer.jpg        starry night over hills (2000x520)
  pattern-warm.png  seamless toy-doodle wallpaper on cream (600x600)
  pattern-cool.png  the same doodles on a pale sky tint (600x600)

Everything is drawn from scratch with Pillow (no stock art), at 2x and scaled
down for smooth edges.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 2

BLUE, CORAL, YELLOW = "#3BA4E6", "#FF7272", "#FFC93C"
MINT, PINK, PURPLE = "#3CCB9A", "#FF8FA8", "#9B87F5"
ORANGE = "#FF9F43"
PALETTE = [BLUE, CORAL, YELLOW, MINT, PINK, PURPLE, ORANGE]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgradient(w, h, stops):
    """Vertical gradient from [(pos 0..1, '#hex'), ...]."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    cols = [(p, hexrgb(c)) for p, c in stops]
    for y in range(h):
        t = y / (h - 1)
        for i in range(len(cols) - 1):
            if cols[i][0] <= t <= cols[i + 1][0]:
                k = (t - cols[i][0]) / max(1e-9, cols[i + 1][0] - cols[i][0])
                c = lerp(cols[i][1], cols[i + 1][1], k)
                break
        for x in range(w):
            px[x, y] = c
    return img


def cloud(d, cx, cy, s, fill="#FFFFFF", shade="#DCEFFC"):
    parts = [(-1.3, .25, .75), (-.6, -.15, 1.0), (.2, -.35, 1.2), (1.0, -.05, .95), (1.6, .3, .7), (0, .3, 1.1)]
    for dx, dy, r in parts:
        d.ellipse([cx + dx * s - r * s, cy + dy * s + s * .12 - r * s, cx + dx * s + r * s, cy + dy * s + s * .12 + r * s], fill=shade)
    for dx, dy, r in parts:
        d.ellipse([cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s], fill=fill)


def hills(d, w, h, base_y, amp, freq, phase, color, step=8):
    pts = [(0, h)]
    for x in range(0, w + step, step):
        y = base_y + amp * math.sin(x * freq + phase) + amp * .45 * math.sin(x * freq * 2.3 + phase * 1.7)
        pts.append((x, y))
    pts.append((w, h))
    d.polygon(pts, fill=color)


def star(d, cx, cy, r, fill, rot=-90):
    pts = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rr = r if i % 2 == 0 else r * .45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def balloon(d, cx, cy, r, color, string_len):
    d.line([cx, cy + r * 1.15, cx + r * .15, cy + r * 1.15 + string_len], fill="#FFFFFF", width=int(r * .06))
    d.polygon([(cx, cy + r * 1.05), (cx - r * .18, cy + r * 1.28), (cx + r * .18, cy + r * 1.28)], fill=color)
    d.ellipse([cx - r * .85, cy - r, cx + r * .85, cy + r * 1.1], fill=color)
    d.ellipse([cx - r * .5, cy - r * .7, cx - r * .15, cy - r * .3], fill="#FFFFFF")


def hero(path):
    W, H = 2000 * SS, 900 * SS
    img = vgradient(W, H, [(0, "#1E90F0"), (.45, "#5BB8F7"), (.78, "#BFE8FF"), (1, "#EAF8FF")])
    d = ImageDraw.Draw(img, "RGBA")
    # sun
    sx, sy = int(W * .60), int(H * .16)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((520, 28), (380, 40), (260, 60)):
        gd.ellipse([sx - r * SS, sy - r * SS, sx + r * SS, sy + r * SS], fill=(255, 235, 140, a))
    glow = glow.filter(ImageFilter.GaussianBlur(40 * SS))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([sx - 95 * SS, sy - 95 * SS, sx + 95 * SS, sy + 95 * SS], fill="#FFE27A")
    d.ellipse([sx - 75 * SS, sy - 75 * SS, sx + 75 * SS, sy + 75 * SS], fill="#FFD23F")
    # clouds (kept away from the left text block)
    for cx, cy, s in ((.50, .30, 80), (.68, .12, 64), (.88, .26, 92), (.97, .08, 58), (.40, .08, 50), (.08, .08, 46)):
        cloud(d, W * cx, H * cy, s * SS)
    # bunting across the top
    pts = []
    for i in range(0, 41):
        t = i / 40
        pts.append((W * t, H * (.045 + .075 * math.sin(math.pi * t))))
    d.line(pts, fill="#FFFFFF", width=3 * SS)
    for i in range(1, 40, 2):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        c = PALETTE[(i // 2) % len(PALETTE)]
        d.polygon([(x0, y0), (x1, y1), ((x0 + x1) / 2, y0 + 62 * SS)], fill=c)
    # balloons
    for bx, by, br, col, sl in ((.455, .44, 38, CORAL, 150), (.49, .50, 32, YELLOW, 130), (.425, .52, 30, MINT, 120)):
        balloon(d, W * bx, H * by, br * SS, col, sl * SS)
    # kite
    kx, ky = W * .735, H * .42
    k = 54 * SS
    d.polygon([(kx, ky - k), (kx + k * .75, ky), (kx, ky + k * 1.25), (kx - k * .75, ky)], fill=CORAL)
    d.polygon([(kx, ky - k), (kx + k * .75, ky), (kx, ky)], fill=YELLOW)
    d.polygon([(kx, ky), (kx - k * .75, ky), (kx, ky + k * 1.25)], fill=BLUE)
    d.line([kx, ky - k, kx, ky + k * 1.25], fill="#FFFFFF", width=2 * SS)
    d.line([kx - k * .75, ky, kx + k * .75, ky], fill="#FFFFFF", width=2 * SS)
    tail = [(kx, ky + k * 1.25)]
    for i in range(1, 8):
        tail.append((kx + 18 * SS * math.sin(i * 1.1), ky + k * 1.25 + i * 24 * SS))
    d.line(tail, fill="#FFFFFF", width=2 * SS)
    for i, (tx, ty) in enumerate(tail[2::2]):
        d.polygon([(tx, ty), (tx + 16 * SS, ty + 8 * SS), (tx - 4 * SS, ty + 18 * SS)], fill=PALETTE[(i + 1) % len(PALETTE)])
    # stars
    random.seed(4)
    for _ in range(14):
        x, y = random.uniform(.02, .98) * W, random.uniform(.05, .45) * H
        star(d, x, y, random.uniform(7, 15) * SS, (255, 255, 255, 190))
    # hills
    hills(d, W, H, H * .78, 34 * SS, .0030, 0.3, "#8EDC9A")
    hills(d, W, H, H * .84, 30 * SS, .0042, 2.1, "#5CCB86")
    hills(d, W, H, H * .91, 24 * SS, .0050, 4.0, "#34B574")
    # flowers and tufts on the front hill
    random.seed(9)
    for _ in range(46):
        x = random.uniform(0, W)
        y = H * random.uniform(.93, .99)
        col = random.choice([YELLOW, PINK, "#FFFFFF", CORAL])
        r = random.uniform(5, 9) * SS
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        d.ellipse([x - r * .35, y - r * .35, x + r * .35, y + r * .35], fill="#FFB020")
    img = img.convert("RGB").resize((W // SS, H // SS), Image.LANCZOS)
    img.save(path, quality=84, optimize=True, progressive=True)


def footer(path):
    W, H = 2000 * SS, 520 * SS
    img = vgradient(W, H, [(0, "#1B1650"), (.6, "#3A2A8A"), (1, "#5B3FB5")])
    d = ImageDraw.Draw(img, "RGBA")
    random.seed(11)
    for _ in range(70):
        x, y = random.uniform(0, W), random.uniform(0, H * .75)
        r = random.choice([1.5, 2, 2.5, 3.5]) * SS
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randint(70, 150)))
    for _ in range(5):
        star(d, random.uniform(0, W), random.uniform(0, H * .6), random.uniform(8, 12) * SS, random.choice([(255, 226, 122, 150), (255, 255, 255, 140)]))
    mx, my, mr = W * .86, H * .22, 70 * SS
    moon = Image.new("RGBA", img.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)  # plain RGBA mode: the cut-out below writes real transparency
    md.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 243, 196, 150))
    md.ellipse([mx - mr * .62, my - mr * 1.08, mx + mr * 1.38, my + mr * .92], fill=(0, 0, 0, 0))
    img = Image.alpha_composite(img.convert("RGBA"), moon)
    d = ImageDraw.Draw(img, "RGBA")
    hills(d, W, H, H * .80, 30 * SS, .0032, 1.0, (44, 30, 120, 255))
    hills(d, W, H, H * .88, 24 * SS, .0048, 3.2, (30, 20, 95, 255))
    for i in range(34):
        x = W * (i + .5) / 34
        y = H * (.93 + .03 * math.sin(i * 1.7))
        d.ellipse([x - 4 * SS, y - 4 * SS, x + 4 * SS, y + 4 * SS], fill=PALETTE[i % len(PALETTE)])
    img = img.convert("RGB").resize((W // SS, H // SS), Image.LANCZOS)
    img.save(path, quality=84, optimize=True, progressive=True)


def doodle(d, kind, cx, cy, s, col):
    w = max(3, int(s * .13))
    if kind == "star":
        star(d, cx, cy, s * .62, col)
    elif kind == "ring":
        d.ellipse([cx - s * .5, cy - s * .5, cx + s * .5, cy + s * .5], outline=col, width=w)
    elif kind == "block":
        d.rounded_rectangle([cx - s * .45, cy - s * .45, cx + s * .45, cy + s * .45], radius=int(s * .14), fill=col)
        d.line([cx - s * .2, cy, cx + s * .2, cy], fill="#FFFFFF", width=w)
        d.line([cx, cy - s * .2, cx, cy + s * .2], fill="#FFFFFF", width=w)
    elif kind == "tri":
        d.polygon([(cx, cy - s * .5), (cx + s * .5, cy + s * .42), (cx - s * .5, cy + s * .42)], fill=col)
    elif kind == "balloon":
        d.ellipse([cx - s * .36, cy - s * .5, cx + s * .36, cy + s * .34], fill=col)
        d.line([cx, cy + s * .34, cx + s * .08, cy + s * .72], fill=col, width=max(2, w // 2))
    elif kind == "heart":
        r = s * .28
        d.ellipse([cx - 2 * r + r * .1, cy - r * 1.2, cx + r * .1, cy + r * .8], fill=col)
        d.ellipse([cx - r * .1, cy - r * 1.2, cx + 2 * r - r * .1, cy + r * .8], fill=col)
        d.polygon([(cx - 1.95 * r, cy + r * .1), (cx + 1.95 * r, cy + r * .1), (cx, cy + 2.0 * r)], fill=col)
    elif kind == "dot":
        d.ellipse([cx - s * .22, cy - s * .22, cx + s * .22, cy + s * .22], fill=col)
    elif kind == "squiggle":
        pts = [(cx - s * .6 + i * s * .03, cy + math.sin(i * .32) * s * .16) for i in range(41)]
        d.line(pts, fill=col, width=w)


def pattern(path, base):
    T = 600
    img = Image.new("RGB", (T * SS, T * SS), base)
    d = ImageDraw.Draw(img, "RGBA")
    kinds = ["star", "ring", "block", "tri", "balloon", "heart", "dot", "squiggle"]
    random.seed(21)
    placed = []
    n = 0
    while len(placed) < 12 and n < 4000:
        n += 1
        x, y = random.uniform(0, T), random.uniform(0, T)
        if all(math.hypot(x - px, y - py) > 150 for px, py in placed):
            placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        col = lerp(hexrgb(base), hexrgb(PALETTE[i % len(PALETTE)]), .30) + (255,)
        s = random.uniform(44, 62) * SS
        for ox in (-T, 0, T):  # wrap so the tile repeats seamlessly
            for oy in (-T, 0, T):
                doodle(d, kinds[i % len(kinds)], (x + ox) * SS, (y + oy) * SS, s, col)
    img = img.resize((T, T), Image.LANCZOS)
    img.save(path, optimize=True)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "static/img/bg"
    os.makedirs(out, exist_ok=True)
    hero(os.path.join(out, "hero.jpg"))
    footer(os.path.join(out, "footer.jpg"))
    pattern(os.path.join(out, "pattern-warm.png"), "#FFF8EC")
    pattern(os.path.join(out, "pattern-cool.png"), "#EEF7FF")
    for f in sorted(os.listdir(out)):
        print(f, os.path.getsize(os.path.join(out, f)) // 1024, "KB")


if __name__ == "__main__":
    main()
