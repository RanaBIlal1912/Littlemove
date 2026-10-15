"""Draw flat, brand-coloured product illustrations (1000x1000 JPG) for toys
that do not have a photo yet.

    python scripts/make_toy_art.py OUT_DIR [slug ...]

Each file is OUT_DIR/<slug>.jpg. Drawing happens at 2x and is scaled down for
smooth edges. These are illustrations, not photos: replace them from the admin
as real photos become available.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

S = 2  # supersampling
W = 1000

BLUE, BLUE_D = "#3BA4E6", "#2286C8"
CORAL, CORAL_D = "#FF7272", "#E05555"
YELLOW, YELLOW_D = "#FFC93C", "#E8AE1A"
MINT, MINT_D = "#3CCB9A", "#2AAE80"
PINK, PINK_D = "#FF8FA8", "#E8708B"
PURPLE, PURPLE_D = "#9B87F5", "#7C68DB"
WOOD, WOOD_D = "#E4B77C", "#C99556"
INK = "#23314A"
WHITE = "#FFFFFF"
GREY = "#B9C4D0"
SKY = "#CDE9FA"

BG = {
    "blue": ("#E0F2FC", "#C5E6F8"), "mint": ("#DFF7EE", "#C2EEDD"), "coral": ("#FFE8E8", "#FFD2D2"),
    "yellow": ("#FFF3CE", "#FFE8A3"), "pink": ("#FFE8ED", "#FFD0DB"), "purple": ("#ECE8FF", "#D8D0FB"),
}


class Art:
    def __init__(self, bg):
        self.im = Image.new("RGB", (W * S, W * S), BG[bg][0])
        self.d = ImageDraw.Draw(self.im)
        c = BG[bg][1]
        self.d.ellipse((-200 * S, -260 * S, 420 * S, 360 * S), fill=c)
        self.d.ellipse((700 * S, 640 * S, 1260 * S, 1200 * S), fill=c)

    def _p(self, v):
        return [x * S for x in v]

    def ell(self, cx, cy, rx, ry=None, fill=WHITE, outline=None, w=0):
        ry = rx if ry is None else ry
        self.d.ellipse(self._p((cx - rx, cy - ry, cx + rx, cy + ry)), fill=fill, outline=outline, width=w * S)

    def rr(self, x0, y0, x1, y1, r=20, fill=WHITE, outline=None, w=0):
        self.d.rounded_rectangle(self._p((x0, y0, x1, y1)), radius=r * S, fill=fill, outline=outline, width=w * S)

    def poly(self, pts, fill=WHITE):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)

    def line(self, p0, p1, w=10, fill=INK):
        self.d.line([p0[0] * S, p0[1] * S, p1[0] * S, p1[1] * S], fill=fill, width=int(w * S))
        r = w * S / 2
        for x, y in (p0, p1):
            self.d.ellipse((x * S - r, y * S - r, x * S + r, y * S + r), fill=fill)

    def arc(self, cx, cy, r, a0, a1, w=10, fill=INK):
        self.d.arc(self._p((cx - r, cy - r, cx + r, cy + r)), a0, a1, fill=fill, width=int(w * S))

    def shadow(self, cx=500, cy=860, rx=300, ry=34):
        self.ell(cx, cy, rx, ry, fill="#00000018")
        # flatten the alpha-less colour: draw a soft darker ellipse instead
        base = self.im.getpixel((int(cx * S), int((cy + ry + 30) * S)))
        self.ell(cx, cy, rx, ry, fill=tuple(max(0, int(c * .88)) for c in base))

    def save(self, path):
        self.im.resize((W, W), Image.LANCZOS).save(path, quality=92)


def star(a, cx, cy, r, fill):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * .45
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    a.poly(pts, fill)


def wheel(a, x, y, r=46, c=INK, hub=GREY):
    a.ell(x, y, r, fill=c)
    a.ell(x, y, r * .42, fill=hub)


# ---------------------------------------------------------------- drawings
def bug_viewer_jar(a):
    a.shadow()
    a.rr(300, 330, 700, 820, 60, fill="#EAF7FF", outline=BLUE, w=10)
    a.rr(280, 260, 720, 350, 28, fill=YELLOW)
    for x in (330, 400, 470, 540, 610, 680):
        a.line((x, 280), (x, 335), 8, YELLOW_D)
    a.ell(500, 640, 70, 52, fill=CORAL)
    a.ell(500, 585, 34, 30, fill=INK)
    for dx in (-50, -20, 20, 50):
        a.line((500 + dx, 650), (500 + dx * 1.7, 705), 8, INK)
    a.line((480, 560), (455, 520), 6, INK)
    a.line((520, 560), (545, 520), 6, INK)
    a.ell(430, 630, 14, fill=INK)
    a.ell(570, 630, 14, fill=INK)
    a.rr(330, 790, 670, 815, 12, fill="#8FD0A0")


def magnifying_glass(a):
    a.shadow()
    a.line((640, 640), (800, 800), 70, WOOD_D)
    a.line((640, 640), (790, 790), 52, WOOD)
    a.ell(430, 430, 235, fill=YELLOW)
    a.ell(430, 430, 190, fill="#E6F6FF")
    a.arc(430, 430, 150, 200, 280, 20, WHITE)
    a.ell(360, 360, 34, 22, fill=WHITE)


def telescope(a):
    a.shadow()
    for p in ((500, 560), (330, 850)), ((500, 560), (500, 850)), ((500, 560), (670, 850)):
        a.line(p[0], p[1], 26, WOOD_D)
    a.poly([(250, 520), (790, 300), (830, 400), (290, 620)], fill=BLUE)
    a.poly([(160, 560), (270, 515), (305, 600), (200, 650)], fill=BLUE_D)
    a.poly([(790, 300), (870, 268), (905, 360), (830, 400)], fill=YELLOW)
    a.ell(500, 560, 38, fill=CORAL)
    star(a, 250, 220, 50, YELLOW)
    star(a, 760, 160, 30, PINK)


def swing_set(a):
    a.shadow(rx=380)
    a.line((200, 200), (120, 850), 34, MINT_D)
    a.line((200, 200), (280, 850), 34, MINT_D)
    a.line((800, 200), (720, 850), 34, MINT_D)
    a.line((800, 200), (880, 850), 34, MINT_D)
    a.line((190, 200), (810, 200), 40, MINT)
    a.line((420, 205), (400, 610), 10, INK)
    a.line((580, 205), (600, 610), 10, INK)
    a.rr(360, 600, 640, 650, 20, fill=CORAL)


def trampoline(a):
    a.shadow(rx=330)
    for x in (250, 400, 600, 750):
        a.line((x, 640), (x - 20 if x < 500 else x + 20, 840), 22, GREY)
    a.ell(500, 560, 360, 120, fill=INK)
    a.ell(500, 540, 330, 100, fill=BLUE)
    a.ell(500, 540, 250, 70, fill=BLUE_D)
    a.ell(500, 540, 150, 40, fill=BLUE)
    for ang in range(0, 360, 30):
        r = math.radians(ang)
        a.ell(500 + 330 * math.cos(r), 540 + 100 * math.sin(r), 10, fill=YELLOW)


def kick_scooter(a):
    a.shadow()
    a.rr(230, 690, 700, 740, 25, fill=CORAL)
    a.line((720, 710), (690, 250), 24, GREY)
    a.line((600, 245), (790, 245), 28, INK)
    a.rr(560, 232, 620, 262, 14, fill=YELLOW)
    a.rr(765, 232, 825, 262, 14, fill=YELLOW)
    wheel(a, 760, 790, 70, INK, YELLOW)
    wheel(a, 240, 790, 60, INK, YELLOW)
    a.line((700, 740), (760, 790), 18, GREY)


def ride_on_car(a):
    a.shadow(rx=330)
    a.rr(190, 520, 810, 740, 70, fill=CORAL)
    a.poly([(320, 520), (390, 380), (610, 380), (690, 520)], fill=CORAL_D)
    a.poly([(355, 520), (405, 410), (500, 410), (500, 520)], fill="#DDF1FF")
    a.poly([(520, 520), (520, 410), (595, 410), (650, 520)], fill="#DDF1FF")
    a.ell(260, 610, 28, fill=YELLOW)
    a.ell(745, 600, 28, fill=YELLOW)
    wheel(a, 300, 760, 70, INK, YELLOW)
    wheel(a, 700, 760, 70, INK, YELLOW)
    a.rr(450, 640, 560, 665, 12, fill=CORAL_D)


def slide_climb(a):
    a.shadow(rx=400)
    a.poly([(520, 230), (880, 800), (790, 810), (480, 330)], fill=YELLOW)
    a.poly([(520, 230), (880, 800), (850, 800), (500, 250)], fill=YELLOW_D)
    a.line((240, 250), (240, 830), 28, BLUE)
    a.line((470, 250), (470, 830), 28, BLUE)
    a.rr(220, 210, 500, 260, 16, fill=CORAL)
    for y in (350, 450, 550, 650, 750):
        a.line((250, y), (460, y), 16, BLUE_D)
    a.line((240, 250), (240, 140), 16, MINT)
    a.line((470, 250), (470, 140), 16, MINT)
    a.rr(225, 120, 485, 150, 14, fill=MINT)


def kite(a):
    a.shadow(cy=900, rx=200, ry=18)
    a.poly([(500, 90), (760, 380), (500, 700), (240, 380)], fill=CORAL)
    a.poly([(500, 90), (760, 380), (500, 380)], fill=YELLOW)
    a.poly([(500, 380), (240, 380), (500, 700)], fill=BLUE)
    a.poly([(500, 380), (760, 380), (500, 700)], fill=MINT)
    a.line((500, 90), (500, 700), 8, WHITE)
    a.line((240, 380), (760, 380), 8, WHITE)
    pts = [(500, 700)]
    for i in range(1, 13):
        pts.append((500 + 55 * math.sin(i * 1.1), 700 + i * 20))
    for p, q in zip(pts, pts[1:]):
        a.line(p, q, 8, INK)
    for i, c in enumerate((YELLOW, CORAL, BLUE)):
        x, y = pts[3 + i * 3]
        a.poly([(x - 36, y - 20), (x + 36, y - 20), (x, y + 24)], fill=c)


def balloons(a):
    a.shadow(cy=930, ry=16, rx=220)
    for cx, cy, c, d in ((330, 330, CORAL, CORAL_D), (500, 250, YELLOW, YELLOW_D), (670, 330, BLUE, BLUE_D), (500, 450, MINT, MINT_D)):
        a.line((cx, cy + 130), (500 + (cx - 500) * .2, 900), 6, GREY)
        a.ell(cx, cy, 115, 140, fill=c)
        a.poly([(cx - 18, cy + 135), (cx + 18, cy + 135), (cx, cy + 165)], fill=d)
        a.ell(cx - 40, cy - 50, 22, 36, fill=_lighten(c))


def _lighten(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(int(v + (255 - v) * .55) for v in (r, g, b))


def flying_disc(a):
    a.shadow(rx=330)
    a.ell(500, 560, 360, 130, fill=PURPLE_D)
    a.ell(500, 530, 360, 130, fill=PURPLE)
    a.ell(500, 530, 270, 90, fill=PURPLE_D)
    a.ell(500, 520, 250, 80, fill=PURPLE)
    a.arc(500, 520, 210, 200, 340, 10, "#C9BEFB")
    star(a, 500, 520, 40, YELLOW)


def catch_ball(a):
    a.shadow(rx=330)
    a.ell(330, 620, 170, fill=BLUE)
    a.ell(270, 560, 46, 30, fill=_lighten(BLUE))
    a.ell(700, 500, 135, fill=CORAL)
    a.ell(655, 450, 36, 24, fill=_lighten(CORAL))
    a.ell(560, 780, 80, fill=YELLOW)
    a.ell(535, 755, 22, 14, fill=_lighten(YELLOW))
    a.arc(330, 620, 170, 20, 80, 12, BLUE_D)
    a.arc(700, 500, 135, 20, 80, 10, CORAL_D)


def bubble_wand(a):
    a.shadow()
    a.rr(450, 480, 520, 830, 34, fill=MINT)
    a.ell(485, 340, 150, fill=None, outline=MINT_D, w=26)
    for cx, cy, r in ((720, 260, 90), (780, 470, 55), (230, 230, 65), (640, 620, 40), (300, 520, 30)):
        a.ell(cx, cy, r, fill="#EAF7FF", outline=BLUE, w=6)
        a.ell(cx - r * .3, cy - r * .3, r * .18, fill=WHITE)


def sand_timer(a):
    a.shadow(rx=240)
    a.rr(260, 150, 740, 215, 24, fill=WOOD_D)
    a.rr(260, 800, 740, 865, 24, fill=WOOD_D)
    a.poly([(300, 215), (700, 215), (540, 500), (700, 800), (300, 800), (460, 500)], fill="#E8F6FF")
    a.poly([(340, 250), (660, 250), (520, 430), (480, 430)], fill=YELLOW)
    a.poly([(500, 520), (520, 520), (600, 780), (400, 780)], fill=YELLOW)
    a.line((500, 430), (500, 700), 6, YELLOW_D)
    a.line((280, 215), (280, 800), 18, WOOD)
    a.line((720, 215), (720, 800), 18, WOOD)


def water_table(a):
    a.shadow(rx=330)
    for x in (260, 740):
        a.line((x, 560), (x - 30 if x < 500 else x + 30, 830), 30, BLUE_D)
    a.rr(150, 380, 850, 600, 70, fill=BLUE)
    a.rr(190, 410, 810, 560, 50, fill=SKY)
    a.rr(190, 470, 810, 560, 40, fill="#7CC4F0")
    a.ell(470, 450, 55, 40, fill=YELLOW)
    a.ell(420, 425, 28, fill=YELLOW)
    a.poly([(390, 428), (360, 436), (390, 446)], fill=CORAL)
    a.ell(612, 480, 28, fill=WHITE)
    a.ell(660, 440, 18, fill=WHITE)


def bean_bag_toss(a):
    a.shadow(rx=360)
    a.poly([(260, 230), (740, 230), (820, 790), (180, 790)], fill=WOOD)
    a.poly([(260, 230), (740, 230), (760, 340), (240, 340)], fill=WOOD_D)
    for cx, cy, c in ((500, 420, CORAL), (360, 560, BLUE), (640, 560, MINT)):
        a.ell(cx, cy, 70, fill=INK)
        a.ell(cx, cy, 58, fill="#5a3b22")
    a.rr(420, 740, 520, 810, 20, fill=YELLOW)
    a.rr(560, 770, 660, 840, 20, fill=CORAL)
    a.rr(300, 790, 400, 850, 20, fill=BLUE)


def mini_basketball(a):
    a.shadow(rx=280)
    a.line((500, 330), (500, 850), 28, GREY)
    a.rr(380, 800, 620, 850, 20, fill=BLUE_D)
    a.rr(260, 130, 740, 380, 22, fill=WHITE, outline=INK, w=8)
    a.rr(400, 230, 600, 360, 6, fill=None, outline=CORAL, w=10)
    a.arc(500, 400, 100, 0, 180, 14, CORAL)
    for x in (410, 450, 500, 550, 590):
        a.line((x, 400), (500 + (x - 500) * .5, 500), 5, WHITE)
    a.ell(780, 620, 120, fill=CORAL)
    a.arc(780, 620, 120, 300, 60, 8, INK)
    a.arc(780, 620, 120, 120, 240, 8, INK)
    a.line((660, 620), (900, 620), 8, INK)
    a.line((780, 500), (780, 740), 8, INK)


def soccer_ball(a):
    a.shadow(rx=260)
    a.ell(500, 540, 290, fill=WHITE, outline=INK, w=10)
    for cx, cy in ((500, 540), (330, 420), (670, 420), (390, 700), (610, 700)):
        pts = [(cx + 62 * math.cos(math.radians(a0 - 90)), cy + 62 * math.sin(math.radians(a0 - 90))) for a0 in range(0, 360, 72)]
        a.poly(pts, fill=INK)
    for p, q in (((500, 540), (500, 400)), ((330, 420), (400, 380)), ((670, 420), (600, 380))):
        a.line(p, q, 6, INK)


def jump_rope(a):
    a.shadow(rx=330)
    a.rr(120, 170, 260, 330, 50, fill=CORAL)
    a.rr(740, 170, 880, 330, 50, fill=CORAL)
    a.rr(120, 170, 260, 215, 22, fill=CORAL_D)
    a.rr(740, 170, 880, 215, 22, fill=CORAL_D)
    pts = []
    for i in range(0, 41):
        t = i / 40
        pts.append((190 + t * 620, 320 + 520 * math.sin(math.pi * t) ** 1.2))
    for p, q in zip(pts, pts[1:]):
        a.line(p, q, 20, BLUE)


def hula_hoop(a):
    a.shadow(rx=300)
    a.ell(500, 490, 340, 390, fill=None, outline=PINK, w=60)
    n = 18
    for i in range(n):
        a0 = i * 2 * math.pi / n
        x, y = 500 + 340 * math.cos(a0), 490 + 390 * math.sin(a0)
        a.ell(x, y, 29, fill=[YELLOW, MINT, BLUE, CORAL][i % 4])


def balance_beam(a):
    a.shadow(rx=380)
    for x in (230, 770):
        a.rr(x - 30, 560, x + 30, 840, 14, fill=WOOD_D)
    a.rr(120, 470, 880, 580, 24, fill=WOOD)
    a.rr(120, 470, 880, 500, 16, fill="#F1CE9F")
    a.rr(120, 560, 880, 580, 12, fill=WOOD_D)
    for x in (260, 420, 580, 740):
        a.ell(x, 525, 12, fill=WOOD_D)


def climbing_set(a):
    a.shadow(rx=380)
    a.line((180, 840), (500, 180), 34, WOOD_D)
    a.line((820, 840), (500, 180), 34, WOOD_D)
    for y, x in ((300, 0.80), (420, 0.60), (540, 0.40), (660, 0.20)):
        t = (y - 180) / 660
        xl, xr = 500 - 320 * t, 500 + 320 * t
        a.line((xl + 22, y), (xr - 22, y), 22, [CORAL, YELLOW, MINT, BLUE][int((y - 300) / 120)])
    a.line((500, 180), (500, 820), 18, WOOD)
    a.ell(500, 170, 38, fill=CORAL)


def ball_pit(a):
    a.shadow(rx=380)
    a.ell(500, 620, 400, 170, fill=BLUE_D)
    cols = [CORAL, YELLOW, MINT, BLUE, PINK, PURPLE]
    pts = [(330, 560), (420, 520), (520, 500), (610, 520), (690, 560), (260, 600), (370, 610), (480, 590), (590, 600), (700, 610), (770, 600), (320, 660), (430, 670), (540, 660), (650, 670), (440, 450), (550, 440), (380, 500)]
    for i, (x, y) in enumerate(pts):
        a.ell(x, y, 52, fill=cols[i % 6])
        a.ell(x - 16, y - 16, 12, fill=WHITE)
    a.ell(500, 700, 400, 150, fill=None, outline=BLUE_D, w=1)
    a.rr(100, 600, 900, 740, 60, fill=BLUE)
    a.ell(500, 740, 400, 40, fill=BLUE)
    for i, (x, y) in enumerate(pts[:8]):
        a.ell(x, y + 20, 48, fill=cols[(i + 2) % 6])


def activity_gym(a):
    a.shadow(rx=380)
    a.line((140, 850), (500, 170), 30, WOOD_D)
    a.line((860, 850), (500, 170), 30, WOOD_D)
    a.line((330, 500), (670, 500), 20, WOOD)
    a.ell(500, 165, 36, fill=WOOD)
    for x, c in ((400, CORAL), (500, YELLOW), (600, MINT)):
        a.line((x, 500), (x, 600), 6, INK)
    star(a, 400, 650, 60, CORAL)
    a.ell(500, 650, 55, fill=YELLOW)
    a.ell(600, 650, 55, fill=MINT)
    a.ell(500, 640, 14, fill=WHITE)
    a.rr(180, 790, 820, 850, 30, fill=PINK)


def xylophone(a):
    a.shadow(rx=330)
    a.poly([(180, 760), (820, 760), (790, 830), (210, 830)], fill=WOOD_D)
    a.rr(150, 220, 200, 800, 14, fill=WOOD)
    a.rr(800, 220, 850, 800, 14, fill=WOOD)
    cols = [CORAL, "#FF9A5C", YELLOW, MINT, BLUE, PURPLE, PINK]
    for i, c in enumerate(cols):
        x0 = 215 + i * 85
        h = 520 - i * 50
        a.rr(x0, 250 + i * 25, x0 + 72, 250 + i * 25 + h, 18, fill=c)
        a.ell(x0 + 36, 285 + i * 25, 8, fill=WHITE)
        a.ell(x0 + 36, 250 + i * 25 + h - 35, 8, fill=WHITE)
    a.line((880, 830), (700, 640), 12, WOOD_D)
    a.ell(895, 845, 28, fill=CORAL)


def cloth_book(a):
    a.shadow(rx=330)
    a.rr(160, 250, 520, 800, 30, fill=BLUE)
    a.rr(480, 250, 840, 800, 30, fill=BLUE_D)
    a.rr(190, 280, 500, 770, 20, fill=WHITE)
    a.rr(500, 280, 810, 770, 20, fill=WHITE)
    a.ell(345, 520, 110, fill="#B7C6D6")
    a.ell(260, 540, 55, 80, fill="#A4B5C8")
    a.ell(345, 480, 20, fill=INK)
    a.line((380, 540), (420, 700), 40, "#B7C6D6")
    for i, c in enumerate((CORAL, YELLOW, MINT)):
        a.ell(600 + i * 100, 400, 36, fill=c)
    a.rr(560, 520, 750, 700, 22, fill=PINK)
    star(a, 655, 610, 55, YELLOW)


def teething_ring(a):
    a.shadow(rx=280)
    cols = [CORAL, YELLOW, MINT, BLUE, PURPLE, PINK, CORAL, YELLOW]
    n = 8
    for i in range(n):
        ang = i * 2 * math.pi / n - math.pi / 2
        x, y = 500 + 240 * math.cos(ang), 540 + 240 * math.sin(ang)
        a.ell(x, y, 92, 80, fill=cols[i])
        a.ell(x - 20, y - 22, 20, 14, fill=_lighten(cols[i]))
    a.ell(500, 540, 120, fill=BG["blue"][0])


def rattle(a):
    a.shadow(rx=300)
    a.line((350, 560), (650, 560), 40, MINT)
    a.ell(280, 560, 130, fill=CORAL)
    a.ell(720, 560, 130, fill=YELLOW)
    a.ell(280, 560, 70, fill=CORAL_D)
    a.ell(720, 560, 70, fill=YELLOW_D)
    star(a, 280, 560, 45, WHITE)
    a.ell(720, 560, 25, fill=WHITE)
    a.ell(230, 510, 24, 14, fill=_lighten(CORAL))
    a.ell(670, 510, 24, 14, fill=_lighten(YELLOW))


def push_duck(a):
    a.shadow(rx=300)
    a.line((380, 560), (800, 220), 18, WOOD_D)
    a.rr(760, 160, 880, 230, 30, fill=WOOD)
    a.ell(430, 620, 220, 150, fill=YELLOW)
    a.ell(300, 460, 110, fill=YELLOW)
    a.poly([(200, 470), (110, 495), (200, 520)], fill=CORAL)
    a.ell(300, 440, 14, fill=INK)
    a.ell(480, 600, 110, 70, fill=YELLOW_D)
    a.poly([(620, 560), (680, 500), (660, 620)], fill=YELLOW)
    wheel(a, 330, 800, 56, BLUE, WHITE)
    wheel(a, 540, 800, 56, BLUE, WHITE)
    a.line((330, 740), (330, 790), 14, INK)
    a.line((540, 740), (540, 790), 14, INK)


def pull_toy(a):
    a.shadow(rx=330)
    a.rr(250, 440, 700, 700, 90, fill=WOOD)
    a.ell(740, 450, 110, fill=WOOD)
    a.ell(820, 385, 40, 80, fill=WOOD_D)
    a.ell(700, 410, 40, 70, fill=WOOD_D)
    a.ell(760, 440, 12, fill=INK)
    a.ell(840, 480, 22, fill=INK)
    a.rr(220, 500, 270, 600, 25, fill=CORAL)
    for x in (320, 620):
        wheel(a, x, 790, 62, CORAL, YELLOW)
        a.line((x, 700), (x, 740), 16, INK)
    pts = [(210, 560)]
    for i in range(1, 9):
        pts.append((210 - i * 22, 560 + 10 * math.sin(i)))
    for p, q in zip(pts, pts[1:]):
        a.line(p, q, 7, INK)
    a.ell(40, 575, 26, fill=BLUE)


def road_mat(a):
    a.shadow(rx=380)
    a.rr(120, 200, 880, 800, 50, fill=MINT)
    a.rr(120, 200, 880, 800, 50, fill=None, outline=MINT_D, w=10)
    a.rr(180, 440, 820, 560, 10, fill="#4A5568")
    a.rr(440, 260, 560, 740, 10, fill="#4A5568")
    for x in range(200, 810, 90):
        if not 430 < x < 570:
            a.rr(x, 495, x + 50, 506, 4, fill=WHITE)
    for y in range(280, 740, 90):
        if not 430 < y < 570:
            a.rr(495, y, 506, y + 50, 4, fill=WHITE)
    a.rr(230, 270, 380, 380, 18, fill=PINK)
    a.rr(640, 620, 780, 730, 18, fill=YELLOW)
    a.ell(310, 700, 55, fill=BLUE)
    a.ell(700, 330, 50, fill="#5AB87A")


def magnetic_letters(a):
    a.shadow(rx=330)
    tiles = [(180, 300, "A", CORAL), (430, 260, "B", BLUE), (680, 300, "C", YELLOW), (300, 560, "D", MINT), (560, 580, "E", PURPLE)]
    from PIL import ImageFont  # noqa
    for x, y, ch, c in tiles:
        a.rr(x, y, x + 220, y + 240, 36, fill=c)
        a.rr(x, y + 200, x + 220, y + 240, 30, fill=_darken(c))
        _letter(a, ch, x + 110, y + 105, 150, WHITE)


def _darken(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(int(v * .82) for v in (r, g, b))


def _letter(a, ch, cx, cy, size, fill):
    from PIL import ImageFont
    f = ImageFont.truetype(_FONT, size * S)
    bb = a.d.textbbox((0, 0), ch, font=f)
    a.d.text((cx * S - (bb[0] + bb[2]) / 2, cy * S - (bb[1] + bb[3]) / 2), ch, font=f, fill=fill)


def tracing_board(a):
    a.shadow(rx=330)
    a.rr(160, 180, 840, 830, 50, fill=WOOD)
    a.rr(200, 220, 800, 790, 30, fill="#FBEBD2")
    _letter(a, "A", 500, 470, 380, "#E3CDA8")
    a.arc(500, 470, 150, 200, 340, 12, CORAL)
    for i in range(7):
        a.ell(330 + i * 55, 700, 12, fill=BLUE)
    a.ell(330, 700, 26, fill=CORAL)
    a.ell(720, 300, 14, fill=MINT)
    a.line((690, 760), (790, 700), 20, YELLOW)
    a.poly([(790, 700), (820, 684), (800, 722)], fill=INK)


def memory_game(a):
    a.shadow(rx=360)
    cols = [CORAL, BLUE, YELLOW, MINT, PINK, PURPLE]
    k = 0
    for r in range(2):
        for c in range(3):
            x, y = 190 + c * 220, 250 + r * 290
            flip = (r, c) in ((0, 1), (1, 2))
            a.rr(x, y, x + 190, y + 250, 26, fill=WHITE if flip else cols[k], outline=cols[k] if flip else None, w=8)
            if flip:
                a.ell(x + 95, y + 110, 62, fill=cols[k])
                a.ell(x + 70, y + 60, 24, fill=cols[k])
                a.ell(x + 120, y + 60, 24, fill=cols[k])
                a.ell(x + 78, y + 108, 8, fill=WHITE)
                a.ell(x + 112, y + 108, 8, fill=WHITE)
            else:
                star(a, x + 95, y + 125, 52, WHITE)
            k += 1


def tangram(a):
    a.shadow(rx=330)
    a.rr(150, 200, 850, 860, 40, fill=WOOD)
    x0, y0, s = 220, 260, 560
    a.poly([(x0, y0), (x0 + s / 2, y0 + s / 2), (x0, y0 + s)], fill=CORAL)
    a.poly([(x0, y0), (x0 + s, y0), (x0 + s / 2, y0 + s / 2)], fill=BLUE)
    a.poly([(x0 + s, y0), (x0 + s, y0 + s / 2), (x0 + 3 * s / 4, y0 + s / 4)], fill=YELLOW)
    a.poly([(x0 + s / 2, y0 + s / 2), (x0 + 3 * s / 4, y0 + 3 * s / 4), (x0 + s / 2, y0 + s), (x0 + s / 4, y0 + 3 * s / 4)], fill=MINT)
    a.poly([(x0 + s / 2, y0 + s / 2), (x0 + 3 * s / 4, y0 + s / 4), (x0 + s, y0 + s / 2), (x0 + 3 * s / 4, y0 + 3 * s / 4)], fill=PURPLE)
    a.poly([(x0 + s, y0 + s / 2), (x0 + s, y0 + s), (x0 + 3 * s / 4, y0 + 3 * s / 4)], fill=PINK)
    a.poly([(x0 + s / 2, y0 + s), (x0 + 3 * s / 4, y0 + 3 * s / 4), (x0 + s, y0 + s)], fill=YELLOW_D)


def geoboard(a):
    a.shadow(rx=330)
    a.rr(150, 190, 850, 830, 40, fill=WOOD)
    a.rr(190, 230, 810, 790, 24, fill="#FBEBD2")
    pegs = {(r, c): (260 + c * 120, 300 + r * 120) for r in range(5) for c in range(5)}
    path = [(0, 1), (0, 3), (2, 4), (4, 3), (4, 1), (2, 0), (0, 1)]
    for p, q in zip(path, path[1:]):
        a.line(pegs[p], pegs[q], 9, CORAL)
    a.line(pegs[(1, 1)], pegs[(3, 3)], 8, BLUE)
    a.line(pegs[(1, 3)], pegs[(3, 1)], 8, BLUE)
    for (x, y) in pegs.values():
        a.ell(x, y, 17, fill=WOOD_D)
        a.ell(x, y, 8, fill="#F1CE9F")


def fish_puzzle(a):
    a.shadow(rx=360)
    a.rr(130, 190, 870, 830, 44, fill=BLUE)
    a.rr(170, 230, 830, 790, 28, fill=SKY)
    a.ell(430, 480, 190, 120, fill=CORAL)
    a.poly([(580, 480), (720, 390), (720, 570)], fill=CORAL_D)
    a.ell(340, 450, 22, fill=WHITE)
    a.ell(346, 450, 10, fill=INK)
    a.arc(430, 500, 80, 20, 120, 8, WHITE)
    a.ell(660, 700, 100, 60, fill=YELLOW)
    a.poly([(740, 700), (820, 650), (820, 750)], fill=YELLOW_D)
    a.ell(620, 690, 12, fill=INK)
    a.ell(250, 700, 50, 30, fill=MINT)
    a.poly([(290, 700), (330, 680), (330, 720)], fill=MINT_D)
    for x, y in ((300, 300), (560, 290), (700, 300)):
        a.ell(x, y, 18, fill=WHITE, outline=BLUE, w=4)
    a.rr(450, 620, 580, 760, 20, fill=WOOD)
    a.ell(515, 690, 22, fill=WOOD_D)


def building_bricks(a):
    a.shadow(rx=360)

    def brick(x, y, w, c, studs):
        a.rr(x, y, x + w, y + 130, 14, fill=c)
        a.rr(x, y + 100, x + w, y + 130, 14, fill=_darken(c))
        for i in range(studs):
            sx = x + 45 + i * 90
            a.rr(sx - 28, y - 26, sx + 28, y + 6, 10, fill=_darken(c))
            a.rr(sx - 28, y - 30, sx + 28, y, 10, fill=c)
    brick(140, 700, 360, CORAL, 4)
    brick(500, 700, 360, BLUE, 4)
    brick(230, 560, 360, YELLOW, 4)
    brick(590, 560, 270, MINT, 3)
    brick(320, 420, 270, PURPLE, 3)


def toy_vehicles(a):
    a.shadow(rx=400)
    a.rr(120, 560, 450, 730, 36, fill=CORAL)
    a.poly([(190, 560), (240, 450), (380, 450), (420, 560)], fill=CORAL_D)
    a.poly([(215, 560), (255, 470), (320, 470), (320, 560)], fill="#DDF1FF")
    a.poly([(340, 560), (340, 470), (370, 470), (395, 560)], fill="#DDF1FF")
    wheel(a, 210, 735, 52, INK, YELLOW)
    wheel(a, 380, 735, 52, INK, YELLOW)
    a.rr(500, 420, 780, 730, 26, fill=BLUE)
    a.rr(760, 520, 880, 730, 26, fill=BLUE_D)
    a.rr(785, 545, 855, 620, 10, fill="#DDF1FF")
    a.rr(530, 450, 750, 560, 12, fill=WHITE)
    a.rr(530, 590, 750, 700, 12, fill=SKY)
    wheel(a, 590, 735, 52, INK, YELLOW)
    wheel(a, 800, 735, 52, INK, YELLOW)


def dinosaur(a):
    a.shadow(rx=330)
    a.ell(470, 560, 230, 170, fill=MINT)
    a.poly([(240, 560), (80, 640), (250, 640)], fill=MINT)
    a.rr(280, 650, 360, 830, 30, fill=MINT_D)
    a.rr(520, 650, 600, 830, 30, fill=MINT_D)
    a.rr(580, 250, 680, 560, 50, fill=MINT)
    a.ell(700, 280, 100, 80, fill=MINT)
    a.ell(730, 255, 16, fill=WHITE)
    a.ell(735, 255, 7, fill=INK)
    a.arc(740, 300, 40, 20, 140, 8, INK)
    for i, x in enumerate((330, 410, 490, 570)):
        a.poly([(x - 40, 400 + abs(i - 1.5) * 10), (x, 300 + abs(i - 1.5) * 30), (x + 40, 400 + abs(i - 1.5) * 10)], fill=YELLOW)
    for x, y in ((380, 540), (470, 590), (540, 520)):
        a.ell(x, y, 22, fill=MINT_D)


def balance_board(a):
    a.shadow(rx=330)
    a.poly([(300, 760), (700, 760), (640, 640), (360, 640)], fill=WOOD_D)
    a.ell(500, 760, 200, 30, fill=WOOD_D)
    a.poly([(130, 580), (870, 460), (890, 540), (150, 660)], fill=WOOD)
    a.poly([(130, 580), (870, 460), (880, 490), (140, 610)], fill="#F1CE9F")
    for x, y in ((300, 560), (500, 530), (700, 500)):
        a.ell(x, y, 20, fill=WOOD_D)


DRAW = {
    "bug-viewer-jar": (bug_viewer_jar, "mint"), "explorer-magnifying-glass": (magnifying_glass, "yellow"),
    "kids-telescope": (telescope, "blue"), "kids-swing-set": (swing_set, "mint"),
    "mini-trampoline": (trampoline, "blue"), "kids-scooter": (kick_scooter, "coral"),
    "ride-on-toy-car": (ride_on_car, "coral"), "mini-slide-and-climb-set": (slide_climb, "yellow"),
    "kids-kite": (kite, "blue"), "balloon-play-set": (balloons, "pink"),
    "soft-flying-disc": (flying_disc, "purple"), "catch-ball-set": (catch_ball, "mint"),
    "bubble-wand-set": (bubble_wand, "blue"), "sensory-sand-timer": (sand_timer, "yellow"),
    "kids-water-table": (water_table, "blue"), "bean-bag-toss": (bean_bag_toss, "coral"),
    "mini-basketball": (mini_basketball, "yellow"), "soft-soccer-ball": (soccer_ball, "mint"),
    "kids-jump-rope": (jump_rope, "pink"), "kids-hula-hoop": (hula_hoop, "purple"),
    "wooden-balance-beam": (balance_beam, "blue"), "wooden-climbing-set": (climbing_set, "mint"),
    "soft-ball-pit": (ball_pit, "pink"), "baby-activity-gym": (activity_gym, "yellow"),
    "rainbow-xylophone": (xylophone, "purple"), "soft-cloth-book": (cloth_book, "pink"),
    "chunky-teething-ring": (teething_ring, "blue"), "rattle-toy": (rattle, "mint"),
    "push-along-duck": (push_duck, "yellow"), "pull-along-toy": (pull_toy, "coral"),
    "road-play-mat": (road_mat, "mint"), "magnetic-letters-set": (magnetic_letters, "blue"),
    "letter-tracing-board": (tracing_board, "yellow"), "animal-memory-game": (memory_game, "purple"),
    "tangram-puzzle": (tangram, "coral"), "rubber-band-geoboard": (geoboard, "mint"),
    "ocean-fish-puzzle": (fish_puzzle, "blue"), "building-bricks-set": (building_bricks, "coral"),
    "toy-vehicles-set": (toy_vehicles, "yellow"), "dinosaur-figures": (dinosaur, "mint"),
    "wooden-balance-board": (balance_board, "pink"),
}

_FONT = None


def _prepare_font():
    global _FONT
    import tempfile
    from fontTools.ttLib import TTFont
    ttf = os.path.join(tempfile.mkdtemp(prefix="lm_art_"), "f.ttf")
    f = TTFont(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts", "fredoka-latin-700-normal.woff2"))
    f.flavor = None
    f.save(ttf)
    _FONT = ttf


def main():
    out = sys.argv[1]
    only = sys.argv[2:] or list(DRAW)
    os.makedirs(out, exist_ok=True)
    _prepare_font()
    for slug in only:
        fn, bg = DRAW[slug]
        art = Art(bg)
        fn(art)
        art.save(os.path.join(out, slug + ".jpg"))
    print(len(only), "illustrations ->", out)


if __name__ == "__main__":
    main()
