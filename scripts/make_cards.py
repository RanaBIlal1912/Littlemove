"""Generate LittleMove social/marketing cards (1080x1080 PNG).

    python scripts/make_cards.py OUT_DIR [PHOTO_DIR]

OUT_DIR   where the PNGs are written.
PHOTO_DIR folder holding the product pictures named in PRODUCTS (optional;
          product cards are skipped for photos that are missing).

Needs Pillow, fonttools and brotli (fonts are converted from the site's woff2).
"""
import os
import sys
import tempfile

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "static", "fonts")
LOGO = os.path.join(ROOT, "static", "img", "littlemove-logo.png")

SIZE = 1080
INK = "#23314A"
MUTED = "#6B7A8D"
CREAM = "#FFFBF3"
WHITE = "#FFFFFF"
WA = "#25D366"
PALETTE = {
    "blue": ("#3BA4E6", "#E0F2FC"),
    "mint": ("#3CCB9A", "#DFF7EE"),
    "coral": ("#FF7272", "#FFE8E8"),
    "yellow": ("#FFC93C", "#FFF3CE"),
    "pink": ("#FF8FA8", "#FFE8ED"),
    "purple": ("#9B87F5", "#ECE8FF"),
}
WHATSAPP = "+92 310 6521912"
SITE = "littlemove.onrender.com"

SKILLS = [
    ("Fine motor", "Grip, stack, thread and pinch.", "blue"),
    ("Social & Emotional", "Play together, feel and share.", "pink"),
    ("Speech & language", "First words, sounds and talking games.", "yellow"),
    ("Sensory play", "Textures, squeezes and calm-down tools.", "mint"),
    ("Gross motor", "Balance, crawl, jump and climb.", "coral"),
    ("Thinking & puzzles", "Shapes, colours and problem solving.", "purple"),
]

INFO = [
    ("welcome", "blue", "Play. Learn. Grow.",
     "Toys that help little ones grow, chosen with therapists.", "Little steps, big dreams"),
    ("free-delivery", "mint", "Free delivery",
     "On every order of Rs 5,000 or more, across Pakistan.", "Fast and safe at your door"),
    ("cash-on-delivery", "yellow", "Cash on delivery",
     "Pay the rider when the parcel arrives. No advance needed.", "Order now, pay later"),
    ("therapist-chosen", "coral", "Therapist chosen",
     "Safe, age-right toys picked at Wellness Rehabilitation Clinic, Bahawalpur.", "Made for growing minds"),
    ("easy-replacement", "purple", "Damaged? We replace it",
     "If your toy arrives damaged, message us and we will send a new one.", "Shop with confidence"),
    ("order-on-whatsapp", "mint", "Order on WhatsApp",
     f"Tell us the toy and your child's age. We reply fast.  {WHATSAPP}", "Chat with us anytime"),
    ("thank-you", "pink", "Thank you!",
     "Your support means the world to us. We hope your little one enjoys every moment of play.",
     "Little steps, big dreams"),
]

# (file, product name, price, old price or None, colour, photo file in PHOTO_DIR)
PRODUCTS = [
    ("colour-building-blocks", "Colour Building Blocks", 2200, None, "yellow", "p12.jpg"),
    ("shape-sorter-box", "Shape Sorter Box", 2350, 2450, "blue", "p10.jpg"),
    ("calm-down-squeeze-kit", "Calm Down Squeeze Kit", 1150, 1400, "mint", "KT-120.jpg"),
    ("sensory-ball-set", "Sensory Ball Set", 1350, None, "coral", "p6.jpg"),
    ("threading-beads-set", "Threading Beads Set", 2000, None, "pink", "p2.jpg"),
    ("rainbow-stacking-rings", "Rainbow Stacking Rings", 1450, None, "purple", "p1.jpg"),
]

_font_cache = {}
_tmp = tempfile.mkdtemp(prefix="lm_fonts_")


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        ttf = os.path.join(_tmp, name + ".ttf")
        if not os.path.exists(ttf):
            f = TTFont(os.path.join(FONT_DIR, name + ".woff2"))
            f.flavor = None
            f.save(ttf)
        _font_cache[key] = ImageFont.truetype(ttf, size)
    return _font_cache[key]


def display(size):
    return font("fredoka-latin-700-normal", size)


def body(size, weight="700"):
    return font(f"nunito-sans-latin-{weight}-normal", size)


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def centered(draw, y, text, fnt, fill, max_w=860, gap=1.18):
    for line in wrap(draw, text, fnt, max_w):
        w = draw.textlength(line, font=fnt)
        draw.text(((SIZE - w) / 2, y), line, font=fnt, fill=fill)
        y += int(fnt.size * gap)
    return y


def logo_circle(d):
    im = Image.open(LOGO).convert("RGBA")
    w, h = im.size
    r = int(min(w, h) * 0.44)
    im = im.crop((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r)).resize((d, d), Image.LANCZOS)
    backing = Image.new("RGBA", (d, d), "white")
    backing.alpha_composite(im)
    im = backing
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d, d), fill=255)
    im.putalpha(mask)
    return im


def base(colour):
    strong, soft = PALETTE[colour]
    img = Image.new("RGB", (SIZE, SIZE), soft)
    d = ImageDraw.Draw(img)
    # soft decorative blobs
    d.ellipse((-220, -220, 420, 420), fill=_mix(strong, soft, .25))
    d.ellipse((760, 700, 1300, 1240), fill=_mix(strong, soft, .25))
    d.ellipse((880, -140, 1200, 180), fill=_mix(strong, soft, .12))
    return img, d


def _mix(a, b, t):
    a = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(b[i] + (a[i] - b[i]) * t) for i in range(3))


def footer(img, d, colour):
    strong = PALETTE[colour][0]
    img.paste(logo_circle(120), (60, SIZE - 180), logo_circle(120))
    d.text((200, SIZE - 172), "LittleMove", font=display(46), fill=INK)
    d.text((200, SIZE - 118), f"WhatsApp {WHATSAPP}", font=body(28, "800"), fill=INK)
    d.text((200, SIZE - 82), SITE, font=body(24), fill=MUTED)
    d.rounded_rectangle((SIZE - 400, SIZE - 150, SIZE - 60, SIZE - 80), 35, fill=strong)
    t = "Play · Learn · Grow"
    w = d.textlength(t, font=body(26, "800"))
    d.text((SIZE - 230 - w / 2, SIZE - 131), t, font=body(26, "800"), fill=WHITE)


def info_card(slug, colour, title, text, tagline, out):
    strong, _ = PALETTE[colour]
    img, d = base(colour)
    d.rounded_rectangle((60, 60, SIZE - 60, SIZE - 220), 60, fill=WHITE)
    y = 240
    d.text(((SIZE - d.textlength(tagline.upper(), font=body(28, "800"))) / 2, 150), tagline.upper(),
           font=body(28, "800"), fill=strong)
    y = centered(d, 330, title, display(110), INK, 820)
    d.rounded_rectangle((SIZE / 2 - 60, y + 20, SIZE / 2 + 60, y + 32), 6, fill=strong)
    centered(d, y + 80, text, body(44, "600"), MUTED, 780, 1.35)
    footer(img, d, colour)
    img.save(os.path.join(out, f"{slug}.png"))


def skill_card(name, line, colour, out):
    strong, _ = PALETTE[colour]
    img, d = base(colour)
    d.rounded_rectangle((60, 60, SIZE - 60, SIZE - 220), 60, fill=WHITE)
    d.text((SIZE / 2 - d.textlength("SHOP BY SKILL", font=body(28, "800")) / 2, 130), "SHOP BY SKILL",
           font=body(28, "800"), fill=strong)
    d.ellipse((SIZE / 2 - 130, 210, SIZE / 2 + 130, 470), fill=PALETTE[colour][1])
    d.ellipse((SIZE / 2 - 80, 260, SIZE / 2 + 80, 420), fill=strong)
    initial = name[0]
    w = d.textlength(initial, font=display(110))
    d.text((SIZE / 2 - w / 2, 270), initial, font=display(110), fill=WHITE)
    y = centered(d, 520, name, display(96), INK, 820)
    centered(d, y + 20, line, body(42, "600"), MUTED, 760, 1.3)
    footer(img, d, colour)
    img.save(os.path.join(out, "skill-" + name.lower().replace(" & ", "-").replace(" ", "-") + ".png"))


def product_card(slug, name, price, old, colour, photo, out):
    strong, soft = PALETTE[colour]
    img, d = base(colour)
    d.rounded_rectangle((60, 60, SIZE - 60, SIZE - 220), 60, fill=WHITE)
    pic = Image.open(photo).convert("RGB")
    s = 560
    side = min(pic.size)
    pic = pic.crop(((pic.width - side) // 2, (pic.height - side) // 2,
                    (pic.width + side) // 2, (pic.height + side) // 2)).resize((s, s), Image.LANCZOS)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s, s), 48, fill=255)
    img.paste(pic, ((SIZE - s) // 2, 100), mask)
    y = centered(d, 690, name, display(70), INK, 860)
    price_txt = f"Rs {price:,}"
    pw = d.textlength(price_txt, font=display(62))
    total = pw
    old_txt = f"Rs {old:,}" if old else ""
    if old:
        total += 30 + d.textlength(old_txt, font=body(40, "700"))
    x = (SIZE - total) / 2
    d.text((x, y + 5), price_txt, font=display(62), fill=strong)
    if old:
        ox = x + pw + 30
        d.text((ox, y + 22), old_txt, font=body(40, "700"), fill=MUTED)
        ow = d.textlength(old_txt, font=body(40, "700"))
        d.line((ox, y + 48, ox + ow, y + 48), fill=MUTED, width=4)
    footer(img, d, colour)
    img.save(os.path.join(out, f"product-{slug}.png"))


def main():
    out = sys.argv[1]
    photos = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(out, exist_ok=True)
    for slug, colour, title, text, tagline in INFO:
        info_card(slug, colour, title, text, tagline, out)
    for name, line, colour in SKILLS:
        skill_card(name, line, colour, out)
    made = 0
    if photos:
        for slug, name, price, old, colour, fname in PRODUCTS:
            p = os.path.join(photos, fname)
            if os.path.exists(p):
                product_card(slug, name, price, old, colour, p, out)
                made += 1
    print(f"{len(INFO)} info + {len(SKILLS)} skill + {made} product cards -> {out}")


if __name__ == "__main__":
    main()
