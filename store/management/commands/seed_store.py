"""Fill an empty shop with starter categories and sample toys.

    python manage.py seed_store

Safe to run more than once: existing categories/products (matched by name) are left alone.
Prices and stock are examples — change them in the admin panel.
"""
from django.core.management.base import BaseCommand

from store.models import Banner, Category, Need, Product, StoreSettings

CATEGORIES = [
    ("Fine motor", "Grip, stack, thread and pinch", "mint"),
    ("Speech & language", "First words, sounds and talking games", "peach"),
    ("Sensory play", "Textures, squeezes and calm-down tools", "sky"),
    ("Gross motor", "Balance, crawl, jump and climb", "sun"),
    ("Thinking & puzzles", "Shapes, colours and problem solving", "lilac"),
]

PRODUCTS = [
    # name, category, price, old price, stock, ages, illustration, featured, pick, summary, helps, box
    ("Rainbow Stacking Rings", "Fine motor", 1450, None, 18, (1, 3), "rings", True, True,
     "Seven wooden rings on a rocking base — the classic first stacking toy.",
     "Hand-eye coordination\nSize ordering\nGrasp and release", "1 wooden base with post\n7 coloured rings"),
    ("Threading Beads Set", "Fine motor", 1250, 1500, 12, (3, 6), "beads", True, False,
     "Chunky wooden beads in five shapes with two lacing strings.",
     "Pincer grip\nBilateral coordination\nPattern copying", "40 wooden beads\n2 lacing strings with stoppers\nPattern cards"),
    ("Play Dough Tool Kit", "Fine motor", 990, None, 25, (3, 7), "dough", False, True,
     "Four tubs of soft, non-toxic dough with rollers and cutters.",
     "Hand strength\nFinger isolation\nCreative play", "4 dough tubs (100 g each)\nRoller and 6 cutters"),
    ("First Words Flash Cards", "Speech & language", 850, None, 30, (1, 4), "cards", True, True,
     "60 thick picture cards of everyday words — animals, food, home and actions.",
     "Vocabulary building\nNaming and pointing\nJoint attention", "60 laminated cards\nParent guide in English and Urdu"),
    ("Action Verbs Picture Cards", "Speech & language", 950, None, 9, (2, 6), "cards", False, False,
     "40 photo cards showing children eating, jumping, sleeping and more.",
     "Two-word phrases\nVerb understanding\nStory telling", "40 photo cards\nGame ideas sheet"),
    ("Sensory Ball Set", "Sensory play", 1350, None, 20, (0, 4), "balls", True, True,
     "Six soft balls with bumps, ridges and dots in different sizes.",
     "Tactile exploration\nGrasping\nCatching and rolling", "6 textured balls (7–10 cm)"),
    ("Calm Down Squeeze Kit", "Sensory play", 1150, 1400, 3, (3, 10), "balls", True, False,
     "A pouch of squishy fidgets for busy hands and big feelings.",
     "Self-regulation\nFocus during homework\nHand strength", "4 squeeze toys\nZip pouch"),
    ("Wooden Balance Board", "Gross motor", 4800, 5500, 6, (2, 8), "board", True, True,
     "A curved rocker board that becomes a bridge, tunnel or see-saw.",
     "Balance and core strength\nBody awareness\nImaginative play", "1 beech balance board (80 cm)"),
    ("Pop-Up Crawl Tunnel", "Gross motor", 2600, None, 8, (1, 5), "tunnel", False, False,
     "A 1.5-metre fold-flat tunnel for crawling games indoors or out.",
     "Crawling and bilateral movement\nSpatial awareness\nTurn-taking games", "1 tunnel with carry bag"),
    ("Shape Sorter Box", "Thinking & puzzles", 1550, None, 15, (1, 3), "shapes", True, False,
     "A wooden box with five shape holes and a lift-off lid.",
     "Shape recognition\nProblem solving\nWrist rotation", "1 wooden box\n10 shape blocks"),
    ("Chunky Animal Puzzle", "Thinking & puzzles", 1100, None, 0, (2, 4), "puzzle", False, False,
     "Six farm animals with big knobs, made for small hands.",
     "Matching\nPincer grip\nAnimal names and sounds", "1 puzzle board\n6 knob pieces"),
    ("Colour Building Blocks", "Thinking & puzzles", 2200, None, 14, (2, 6), "blocks", True, True,
     "50 smooth wooden blocks in shapes and colours that stack well.",
     "Early maths\nColour sorting\nBuilding and planning", "50 wooden blocks\nCotton storage bag"),
]


NEEDS = [
    ("Calm and focus", "For busy hands, big feelings and homework time", "sky"),
    ("First words", "Naming, pointing and early talking", "peach"),
    ("Strong little hands", "Grip, pinch and finger strength for writing later", "mint"),
    ("Movement and balance", "For kids who love to climb, rock and jump", "sun"),
    ("Sensory exploring", "Textures and squeezes for curious hands", "rose"),
    ("Thinking skills", "Matching, sorting and solving", "lilac"),
]
# product name -> needs it is often chosen for
PRODUCT_NEEDS = {
    "Rainbow Stacking Rings": ["Strong little hands", "Thinking skills"],
    "Threading Beads Set": ["Strong little hands", "Calm and focus"],
    "Play Dough Tool Kit": ["Strong little hands", "Sensory exploring", "Calm and focus"],
    "First Words Flash Cards": ["First words"],
    "Action Verbs Picture Cards": ["First words", "Thinking skills"],
    "Sensory Ball Set": ["Sensory exploring", "Movement and balance"],
    "Calm Down Squeeze Kit": ["Calm and focus", "Sensory exploring"],
    "Wooden Balance Board": ["Movement and balance", "Calm and focus"],
    "Pop-Up Crawl Tunnel": ["Movement and balance"],
    "Shape Sorter Box": ["Thinking skills", "Strong little hands"],
    "Chunky Animal Puzzle": ["Thinking skills", "First words"],
    "Colour Building Blocks": ["Thinking skills", "Strong little hands"],
}

BANNERS = [
    ("Toys that help little ones grow",
     "Sensory, motor and speech toys chosen with therapists. Cash on delivery across Pakistan.",
     "Shop all toys", "/shop/", "purple", "rings"),
    ("Sale on parents' favourites",
     "Balance boards, threading beads and calm-down kits at lower prices this month.",
     "See the sale", "/shop/?sale=1", "pink", "board"),
    ("First words, made fun",
     "Picture cards and talking games for toddlers starting to speak.",
     "Shop speech toys", "/shop/?category=speech-language", "sky", "cards"),
]


class Command(BaseCommand):
    help = "Add starter categories and sample toys to an empty shop."

    def handle(self, *args, **opts):
        StoreSettings.load()
        cats = {}
        for i, (name, short, color) in enumerate(CATEGORIES):
            cats[name], _ = Category.objects.get_or_create(
                name=name, defaults={"short": short, "color": color, "order": i})

        created = 0
        for (name, cat, price, old, stock, (a, b), ill, feat, pick, summary, helps, box) in PRODUCTS:
            _, new = Product.objects.get_or_create(name=name, defaults=dict(
                category=cats[cat], price=price, compare_at_price=old, stock=stock,
                age_from=a, age_to=b, illustration=ill, is_featured=feat, therapist_pick=pick,
                summary=summary, helps_with=helps, in_the_box=box,
                sku=f"LM-{100 + len(name) + price % 97}",
                description=("A favourite in our therapy sessions. Play alongside your child for "
                             "10–15 minutes a day and follow their lead — short, happy sessions work best."),
            ))
            created += new
        needs = {}
        for i, (name, short, color) in enumerate(NEEDS):
            needs[name], _ = Need.objects.get_or_create(
                name=name, defaults={"short": short, "color": color, "order": i})
        for pname, nlist in PRODUCT_NEEDS.items():
            product = Product.objects.filter(name=pname).first()
            if product and not product.needs.exists():
                product.needs.set([needs[n] for n in nlist])

        if not Banner.objects.exists():
            for i, (title, sub, btn, link, style, ill) in enumerate(BANNERS):
                Banner.objects.create(title=title, subtitle=sub, button_text=btn, link=link,
                                      style=style, illustration=ill, order=i)

        self.stdout.write(self.style.SUCCESS(
            f"Ready: {len(cats)} categories, {created} new products ({Product.objects.count()} total)."))
