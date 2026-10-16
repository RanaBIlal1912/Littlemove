"""Draw four original cartoon children for the "Shop by little one" cards.

    python scripts/make_kids.py static/img/kids

Writes baby.png, toddler.png, kid.png and bigkid.png (600x600, transparent).
Flat shapes only, drawn at 2x and scaled down for smooth edges.
"""
import os
import sys

from PIL import Image, ImageDraw

SS = 2
W = 600

SKIN, SKIN_D = "#F7C9A0", "#EBA977"
INK = "#2B2342"
CHEEK = "#FF9C9C"


def new():
    img = Image.new("RGBA", (W * SS, W * SS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def e(d, cx, cy, rx, ry, fill, outline=None, width=0):
    d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill, outline=outline, width=width * SS)


def rr(d, x0, y0, x1, y1, r, fill):
    d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=fill)


def poly(d, pts, fill):
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)


def face(d, cx, cy, s=1.0, glasses=False):
    """Eyes, brows, cheeks and a smile centred on (cx, cy)."""
    for dx in (-52, 52):
        e(d, cx + dx * s, cy, 15 * s, 19 * s, INK)
        e(d, cx + dx * s + 5 * s, cy - 6 * s, 5 * s, 6 * s, "#FFFFFF")
        e(d, cx + dx * s * 1.55, cy + 40 * s, 17 * s, 11 * s, CHEEK)
    # smile
    d.arc([(cx - 34 * s) * SS, (cy + 6 * s) * SS, (cx + 34 * s) * SS, (cy + 58 * s) * SS], 15, 165, fill=INK, width=int(7 * s * SS))
    e(d, cx, cy + 40 * s, 22 * s, 13 * s, "#FF7A7A")
    d.rectangle([(cx - 30 * s) * SS, (cy + 22 * s) * SS, (cx + 30 * s) * SS, (cy + 36 * s) * SS], fill=SKIN)
    d.arc([(cx - 34 * s) * SS, (cy + 6 * s) * SS, (cx + 34 * s) * SS, (cy + 58 * s) * SS], 15, 165, fill=INK, width=int(7 * s * SS))


def head(d, cx, cy, r, ear=True):
    if ear:
        e(d, cx - r, cy + 8, 22, 28, SKIN_D)
        e(d, cx + r, cy + 8, 22, 28, SKIN_D)
    e(d, cx, cy, r, r * 1.02, SKIN)


def hand(d, x, y, r=24):
    e(d, x, y, r, r, SKIN)


def baby():
    img, d = new()
    # onesie with bear-ear hood
    e(d, 300, 160, 125, 125, "#7DD9B8")                  # hood behind head
    e(d, 190, 70, 40, 40, "#7DD9B8"); e(d, 190, 70, 22, 22, "#BFF0DD")
    e(d, 410, 70, 40, 40, "#7DD9B8"); e(d, 410, 70, 22, 22, "#BFF0DD")
    rr(d, 130, 330, 470, 600, 120, "#7DD9B8")           # body
    e(d, 300, 470, 70, 80, "#A8E8CF")                    # tummy patch
    head(d, 300, 215, 105, ear=False)
    # hood front trim
    d.arc([(300 - 118) * SS, (215 - 118) * SS, (300 + 118) * SS, (215 + 118) * SS], 195, 345, fill="#7DD9B8", width=18 * SS)
    # tuft
    d.arc([260 * SS, 100 * SS, 340 * SS, 150 * SS], 200, 340, fill="#8A5A3C", width=8 * SS)
    face(d, 300, 215, 0.8)
    # arms up holding a rattle
    rr(d, 80, 360, 170, 470, 44, "#7DD9B8"); hand(d, 120, 345)
    rr(d, 430, 360, 520, 470, 44, "#7DD9B8"); hand(d, 480, 345)
    # stacking-ring toy in the right hand
    rr(d, 474, 215, 486, 345, 5, "#E8B26F")
    e(d, 480, 205, 38, 14, "#FF7272"); e(d, 480, 180, 30, 12, "#FFC93C"); e(d, 480, 158, 22, 10, "#3BA4E6")
    return img


def toddler():
    img, d = new()
    # blue tee with a star
    rr(d, 120, 345, 480, 600, 110, "#4DA8F0")
    e(d, 300, 470, 0, 0, "#FFFFFF")
    pts = []
    import math
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr_ = 52 if i % 2 == 0 else 22
        pts.append((300 + rr_ * math.cos(a), 470 + rr_ * math.sin(a)))
    poly(d, pts, "#FFD54A")
    head(d, 300, 220, 108)
    # curly dark hair
    for dx, dy, r in ((-85, -62, 42), (-35, -102, 46), (30, -108, 46), (82, -70, 42), (110, -20, 30), (-112, -18, 30)):
        e(d, 300 + dx, 220 + dy, r, r, "#5B3A29")
    face(d, 300, 228, 0.82)
    # arms: left waving, right holding a block
    rr(d, 70, 330, 160, 470, 46, "#4DA8F0"); hand(d, 112, 318)
    rr(d, 440, 380, 530, 500, 46, "#4DA8F0"); hand(d, 486, 505)
    rr(d, 440, 470, 560, 590, 18, "#FF7272")
    e(d, 500, 530, 22, 22, "#FFFFFF"); d.line([(488 * SS, 530 * SS), (512 * SS, 530 * SS)], fill="#FF7272", width=7 * SS)
    d.line([(500 * SS, 518 * SS), (500 * SS, 542 * SS)], fill="#FF7272", width=7 * SS)
    return img


def kid():
    img, d = new()
    # yellow hoodie
    rr(d, 110, 340, 490, 600, 120, "#FFC93C")
    e(d, 300, 360, 90, 40, "#F2B41F")
    rr(d, 255, 400, 345, 470, 22, "#F2B41F")
    d.line([(280 * SS, 345 * SS), (280 * SS, 440 * SS)], fill="#FFFFFF", width=5 * SS)
    d.line([(320 * SS, 345 * SS), (320 * SS, 440 * SS)], fill="#FFFFFF", width=5 * SS)
    head(d, 300, 215, 106)
    # swept dark hair
    poly(d, [(190, 205), (205, 120), (300, 88), (400, 120), (410, 205), (380, 150), (300, 135), (225, 155)], "#3B2A22")
    e(d, 300, 120, 100, 40, "#3B2A22")
    face(d, 300, 225, 0.82)
    # holding a toy car
    rr(d, 80, 400, 170, 540, 46, "#FFC93C"); hand(d, 135, 545)
    rr(d, 430, 380, 520, 520, 46, "#FFC93C"); hand(d, 482, 525)
    rr(d, 95, 500, 285, 560, 26, "#FF5A5F")
    rr(d, 135, 468, 245, 515, 20, "#FF5A5F")
    rr(d, 150, 478, 228, 508, 8, "#BFE6FF")
    e(d, 140, 568, 24, 24, INK); e(d, 140, 568, 10, 10, "#CFCFCF")
    e(d, 245, 568, 24, 24, INK); e(d, 245, 568, 10, 10, "#CFCFCF")
    return img


def bigkid():
    img, d = new()
    # pigtails
    e(d, 118, 250, 44, 80, "#2F1F1A"); e(d, 482, 250, 44, 80, "#2F1F1A")
    e(d, 118, 160, 26, 26, "#FF8FB1"); e(d, 482, 160, 26, 26, "#FF8FB1")
    # coral top with collar
    rr(d, 115, 340, 485, 600, 115, "#FF7B7B")
    poly(d, [(240, 345), (300, 420), (360, 345), (335, 340), (300, 380), (265, 340)], "#FFFFFF")
    head(d, 300, 215, 106, ear=False)
    # hair cap with fringe
    e(d, 300, 150, 112, 70, "#2F1F1A")
    poly(d, [(195, 150), (230, 205), (270, 150), (300, 210), (345, 150), (380, 205), (405, 150)], "#2F1F1A")
    face(d, 300, 232, 0.82)
    # hair clips
    e(d, 218, 140, 16, 12, "#FFD54A"); e(d, 382, 140, 16, 12, "#FFD54A")
    # hugging a teddy bear
    e(d, 300, 520, 125, 80, "#C99456")
    e(d, 205, 450, 30, 30, "#C99456"); e(d, 395, 450, 30, 30, "#C99456")
    e(d, 205, 450, 15, 15, "#E6BE8A"); e(d, 395, 450, 15, 15, "#E6BE8A")
    e(d, 300, 470, 90, 70, "#D9A86C")
    e(d, 262, 470, 10, 12, INK); e(d, 338, 470, 10, 12, INK)
    e(d, 300, 500, 28, 20, "#F3D2A2"); e(d, 300, 494, 10, 7, INK)
    rr(d, 85, 430, 190, 570, 48, "#FF7B7B"); hand(d, 175, 520)
    rr(d, 410, 430, 515, 570, 48, "#FF7B7B"); hand(d, 425, 520)
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "static/img/kids"
    os.makedirs(out, exist_ok=True)
    for name, fn in (("baby", baby), ("toddler", toddler), ("kid", kid), ("bigkid", bigkid)):
        img = fn().resize((W, W), Image.LANCZOS)
        img.save(os.path.join(out, name + ".png"), optimize=True)
        print(name, os.path.getsize(os.path.join(out, name + ".png")) // 1024, "KB")


if __name__ == "__main__":
    main()
