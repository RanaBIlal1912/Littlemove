from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class StoreSettings(models.Model):
    """One row of shop-wide settings, editable from the admin panel."""

    store_name = models.CharField(max_length=80, default="LittleMove")
    tagline = models.CharField(max_length=120, default="Play. Learn. Grow.")
    whatsapp_number = models.CharField(
        max_length=20, default="923173661912",
        help_text="International format without + or spaces, e.g. 923173661912",
    )
    email = models.EmailField(default="littlemoveofficial@gmail.com")
    city = models.CharField(max_length=60, default="Bahawalpur")
    delivery_fee = models.PositiveIntegerField(default=250, help_text="Rs per order")
    free_delivery_over = models.PositiveIntegerField(
        default=5000, help_text="Orders at or above this amount (Rs) ship free. 0 = never free."
    )
    cod_enabled = models.BooleanField("Cash on delivery", default=True)
    jazzcash_number = models.CharField(max_length=20, blank=True, default="03173661912")
    easypaisa_number = models.CharField(max_length=20, blank=True, default="03173661912")
    account_title = models.CharField(max_length=80, blank=True, default="LittleMove")
    bank_details = models.TextField(
        blank=True, help_text="Bank name, account title and IBAN. Leave empty to hide bank transfer."
    )
    announcement = models.CharField(
        max_length=300, blank=True,
        default="Free delivery on orders of Rs 5,000 or more",
        help_text="Top bar messages. Separate several with | and they rotate.",
    )
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    tiktok_url = models.URLField("TikTok URL", blank=True)
    youtube_url = models.URLField("YouTube URL", blank=True)

    # Branding
    logo = models.ImageField(
        upload_to="settings/", blank=True,
        help_text="Square logo, 200×200 px or bigger. Shown in admin header.",
    )
    white_logo = models.ImageField(
        upload_to="settings/", blank=True,
        help_text="White/light version of the logo for dark backgrounds.",
    )
    favicon = models.ImageField(
        upload_to="settings/", blank=True,
        help_text="Browser tab icon, 32×32 or 64×64 px.",
    )
    primary_color = models.CharField(
        max_length=20, default="#5B3FD6",
        help_text="Main brand colour (hex, e.g. #5B3FD6). Used for buttons and headings.",
    )
    secondary_color = models.CharField(
        max_length=20, default="#FF4F8B",
        help_text="Secondary brand colour (hex). Used for accents and sale badges.",
    )
    accent_color = models.CharField(
        max_length=20, default="#FFC83D",
        help_text="Highlight colour (hex). Used for stars, badges, etc.",
    )
    background_color = models.CharField(
        max_length=20, default="#F6F3FF",
        help_text="Page background colour (hex).",
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Extra paragraph shown in the website footer.",
    )

    # SEO
    seo_title = models.CharField(
        max_length=120, blank=True,
        help_text="Browser tab title for the home page. Leave blank to use the store name.",
    )
    seo_description = models.CharField(
        max_length=200, blank=True,
        help_text="Meta description shown in Google search results.",
    )
    share_image = models.ImageField(
        upload_to="settings/", blank=True,
        help_text="Image shown when sharing on WhatsApp / social media. Best size: 1200×630.",
    )

    class Meta:
        verbose_name = "Store settings"
        verbose_name_plural = "Store settings"

    def __str__(self):
        return "Store settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # the settings row is permanent

    @property
    def announcements(self):
        return [a.strip() for a in self.announcement.split("|") if a.strip()]

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def delivery_for(self, subtotal):
        if subtotal <= 0:
            return 0
        if self.free_delivery_over and subtotal >= self.free_delivery_over:
            return 0
        return self.delivery_fee


class Category(models.Model):
    """A skill area parents shop by: fine motor, speech, sensory…"""

    COLOR_CHOICES = [
        ("mint", "Mint"), ("peach", "Peach"), ("sky", "Sky"),
        ("lilac", "Lilac"), ("sun", "Sunflower"), ("rose", "Rose"),
    ]

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    short = models.CharField(
        "One-line description", max_length=120, blank=True,
        help_text="Shown on the home page, e.g. 'Grip, stack, thread and pinch'",
    )
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="mint")
    image = models.ImageField(
        upload_to="categories/", blank=True,
        help_text="Optional square photo for the category tile (600×600 or bigger).",
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:shop") + f"?category={self.slug}"


class Need(models.Model):
    """What a parent is looking for help with: calming, focus, first words…"""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    short = models.CharField("One-line description", max_length=120, blank=True)
    color = models.CharField(max_length=10, choices=Category.COLOR_CHOICES, default="lilac")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:shop") + f"?need={self.slug}"


class ProductQuerySet(models.QuerySet):
    def live(self):
        return self.filter(is_active=True, category__is_active=True)


class Product(models.Model):
    ILLUSTRATIONS = [
        ("rings", "Stacking rings"), ("blocks", "Blocks"), ("cards", "Flash cards"),
        ("balls", "Sensory balls"), ("board", "Balance board"), ("puzzle", "Puzzle"),
        ("beads", "Threading beads"), ("tunnel", "Tunnel"), ("dough", "Play dough"),
        ("shapes", "Shape sorter"),
    ]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    needs = models.ManyToManyField(Need, blank=True, related_name="products",
                                   help_text="What parents often choose this toy for.")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    sku = models.CharField("SKU", max_length=40, blank=True)
    price = models.PositiveIntegerField(help_text="Selling price in Rs", validators=[MinValueValidator(1)])
    compare_at_price = models.PositiveIntegerField(
        "Old price", null=True, blank=True, help_text="Optional. Shown crossed out if higher than price."
    )
    stock = models.PositiveIntegerField(default=0)
    age_from = models.PositiveSmallIntegerField("Age from (years)", default=1)
    age_to = models.PositiveSmallIntegerField("Age to (years)", default=6)
    summary = models.CharField(max_length=200, help_text="One or two lines for product cards")
    description = models.TextField(blank=True)
    helps_with = models.TextField(
        blank=True, help_text="One skill per line, e.g. 'Pincer grip'. Shown as a list."
    )
    in_the_box = models.TextField(blank=True, help_text="One item per line.")
    image = models.ImageField(upload_to="products/", blank=True)
    illustration = models.CharField(
        max_length=12, choices=ILLUSTRATIONS, default="blocks",
        help_text="Drawing used until you upload a real photo.",
    )
    is_active = models.BooleanField("Visible in shop", default=True)
    is_featured = models.BooleanField("Show on home page", default=False)
    therapist_pick = models.BooleanField(
        default=False, help_text="Recommended by Wellness Rehabilitation Clinic therapists"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:120] or "product"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product", args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def low_stock(self):
        return 0 < self.stock <= 3

    @property
    def on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_percent(self):
        if not self.on_sale:
            return 0
        return round((self.compare_at_price - self.price) * 100 / self.compare_at_price)

    @property
    def saving(self):
        return (self.compare_at_price - self.price) if self.on_sale else 0

    @property
    def age_label(self):
        if self.age_from == self.age_to:
            return f"{self.age_from} yrs"
        return f"{self.age_from}–{self.age_to} yrs"

    @property
    def helps_with_list(self):
        return [x.strip() for x in self.helps_with.splitlines() if x.strip()]

    @property
    def in_the_box_list(self):
        return [x.strip() for x in self.in_the_box.splitlines() if x.strip()]


class ProductPhoto(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=120, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.alt or f"Photo of {self.product}"


class Banner(models.Model):
    """Home page slider. Upload banners made in Canva or Photoshop."""

    STYLE_CHOICES = [("purple", "Purple"), ("pink", "Pink"), ("sky", "Sky blue"), ("mint", "Mint")]

    title = models.CharField(max_length=80, help_text="Big line, e.g. 'Sensory toys for little explorers'")
    subtitle = models.CharField(max_length=160, blank=True)
    button_text = models.CharField(max_length=30, default="Shop now")
    link = models.CharField(max_length=200, default="/shop/", help_text="Where the banner goes, e.g. /shop/?sale=1")
    image = models.ImageField(
        upload_to="banners/", blank=True,
        help_text="Wide picture, 1600×600. With a photo, the text above is shown on top of it.",
    )
    mobile_image = models.ImageField(
        upload_to="banners/", blank=True, help_text="Optional taller version for phones, 800×800.",
    )
    image_has_text = models.BooleanField(
        default=False, help_text="Tick if your picture already contains the text, so we don't print it twice.",
    )
    style = models.CharField(max_length=10, choices=STYLE_CHOICES, default="purple",
                             help_text="Background colour when there is no picture")
    illustration = models.CharField(max_length=12, choices=Product.ILLUSTRATIONS, default="rings")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    """Real messages from customers (e.g. copied from WhatsApp with permission)."""

    name = models.CharField(max_length=60, help_text="e.g. 'Sana, Multan'")
    text = models.TextField(max_length=400)
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, f"{i} stars") for i in range(1, 6)])
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField("Show on website", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}: {self.text[:40]}"


# ── New models ────────────────────────────────────────────────────────────────

class HomeSection(models.Model):
    """Controls which home-page sections are shown and in what order."""

    HERO_SLIDER = "hero_slider"
    TRUST_BADGES = "trust_badges"
    SHOP_BY_SKILL = "shop_by_skill"
    SHOP_BY_NEED = "shop_by_need"
    FEATURED_PRODUCTS = "featured_products"
    SHOP_BY_AGE = "shop_by_age"
    SALE_PRODUCTS = "sale_products"
    PROMO_BANNERS = "promo_banners"
    NEW_ARRIVALS = "new_arrivals"
    SHOP_BY_BUDGET = "shop_by_budget"
    THERAPIST_PICKS = "therapist_picks"
    VIDEO = "video"
    GALLERY = "gallery"
    TESTIMONIALS = "testimonials"
    WHATSAPP_HELP = "whatsapp_help"
    FAQ_SECTION = "faq"
    SAVE_WITH_BUNDLES = "save_with_bundles"
    OUR_STORY = "our_story"

    SECTION_TYPES = [
        (HERO_SLIDER,        "Hero slider (banners)"),
        (TRUST_BADGES,       "Trust badges"),
        (SHOP_BY_SKILL,      "Shop by skill"),
        (SHOP_BY_NEED,       "Shop by need"),
        (FEATURED_PRODUCTS,  "Featured products"),
        (SHOP_BY_AGE,        "Shop by age"),
        (SALE_PRODUCTS,      "Sale products"),
        (PROMO_BANNERS,      "Promo banners"),
        (NEW_ARRIVALS,       "New arrivals"),
        (SHOP_BY_BUDGET,     "Shop by budget"),
        (THERAPIST_PICKS,    "Therapist picks"),
        (VIDEO,              "Video section"),
        (GALLERY,            "Gallery"),
        (TESTIMONIALS,       "What parents say (testimonials)"),
        (WHATSAPP_HELP,      "WhatsApp help band"),
        (FAQ_SECTION,        "FAQ / Questions parents ask"),
        (SAVE_WITH_BUNDLES,  "Save with bundles"),
        (OUR_STORY,          "Our story"),
    ]

    type = models.CharField(max_length=30, choices=SECTION_TYPES, unique=True,
                            help_text="Each section type can only appear once.")
    title = models.CharField(max_length=120, blank=True,
                             help_text="Custom heading — leave blank to use the default.")
    subtitle = models.CharField(max_length=200, blank=True)
    enabled = models.BooleanField(
        default=True,
        help_text="Untick to hide this section from the home page.",
    )
    order = models.PositiveSmallIntegerField(
        default=0, help_text="Lower numbers appear higher on the page."
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Home page section"
        verbose_name_plural = "Home page sections"

    def __str__(self):
        return self.get_type_display()


class Bundle(models.Model):
    """A curated set of products sold together at a lower combined price."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    products = models.ManyToManyField(
        "Product", related_name="bundles",
        help_text="Choose 2 or more products to include in this bundle.",
    )
    bundle_price = models.PositiveIntegerField(
        help_text="Total price for the whole bundle (Rs). Should be lower than the sum of individual prices.",
        validators=[MinValueValidator(1)],
    )
    image = models.ImageField(
        upload_to="bundles/", blank=True,
        help_text="Optional banner image for the bundle (1200×500 recommended).",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bundle"
        verbose_name_plural = "Bundles"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:120] or "bundle"
            slug, n = base, 2
            while Bundle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:bundle_detail", args=[self.slug])

    @property
    def regular_price(self):
        return sum(p.price for p in self.products.all())

    @property
    def savings(self):
        reg = self.regular_price
        return max(0, reg - self.bundle_price) if reg else 0


class OurStory(models.Model):
    """Singleton: the 'Our story' home page section, editable from admin."""

    title = models.CharField(max_length=120, default="Our story")
    body = models.TextField(
        default=(
            "LittleMove was born at Wellness Rehabilitation Clinic in Bahawalpur. "
            "Our therapists work with children every day and kept meeting the same challenge: "
            "parents wanted to continue the therapy exercises at home, but couldn't find the "
            "right toys in Pakistan.\n\n"
            "So we started selecting the toys we use in our own sessions — sensory, motor and "
            "speech toys that are safe, age-right and actually work. Every toy we sell is one "
            "our therapists have used themselves."
        ),
    )
    photo = models.ImageField(
        upload_to="our_story/", blank=True,
        help_text="A photo of the clinic, team or children playing.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Our story section"
        verbose_name_plural = "Our story section"

    def __str__(self):
        return "Our story"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Popup(models.Model):
    """Sale or offer popup shown to visitors."""

    WHERE_ALL = "all"
    WHERE_HOME = "home"
    WHERE_CHOICES = [
        (WHERE_ALL,  "All pages"),
        (WHERE_HOME, "Home page only"),
    ]

    name = models.CharField(max_length=80, help_text="Internal label — not shown to visitors.")
    title = models.CharField(max_length=120, help_text="Big heading inside the popup.")
    text = models.TextField(blank=True, help_text="Body text below the heading.")
    image = models.ImageField(upload_to="popups/", blank=True,
                              help_text="Optional image for the popup.")
    button_text = models.CharField(max_length=40, default="Shop now")
    button_link = models.CharField(max_length=200, default="/shop/",
                                   help_text="URL the button goes to, e.g. /shop/?sale=1")
    coupon_code = models.CharField(max_length=40, blank=True,
                                   help_text="Optional promo code to display (visitors copy it manually).")
    start_at = models.DateTimeField(null=True, blank=True,
                                    help_text="Leave empty to start showing immediately.")
    end_at = models.DateTimeField(null=True, blank=True,
                                  help_text="Leave empty to show indefinitely.")
    where = models.CharField(max_length=10, choices=WHERE_CHOICES, default=WHERE_ALL)
    delay_seconds = models.PositiveSmallIntegerField(
        default=3, help_text="Seconds after the page loads before the popup appears."
    )
    show_again_days = models.PositiveSmallIntegerField(
        default=7,
        help_text="After a visitor dismisses it, show again after this many days.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-active", "name"]
        verbose_name = "Popup / offer"
        verbose_name_plural = "Popups & offers"

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        from django.db.models import Q
        from django.utils import timezone
        now = timezone.now()
        return (
            cls.objects.filter(active=True)
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
            .first()
        )


class MediaItem(models.Model):
    """Gallery and media library."""

    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_YOUTUBE = "youtube"
    TYPE_CHOICES = [
        (TYPE_IMAGE,   "Image (jpg / png / webp)"),
        (TYPE_VIDEO,   "Video file (mp4 / webm)"),
        (TYPE_YOUTUBE, "YouTube video"),
    ]

    title = models.CharField(max_length=120)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_IMAGE)
    file = models.FileField(
        upload_to="media_library/", blank=True,
        help_text="Image: jpg/png/webp up to 5 MB. Video: mp4/webm up to 50 MB.",
    )
    youtube_url = models.URLField("YouTube URL", blank=True,
                                  help_text="Paste the full YouTube video URL.")
    alt_text = models.CharField(max_length=200, blank=True,
                                help_text="Describe the image for screen readers.")
    show_in_gallery = models.BooleanField(
        default=True, help_text="Tick to show this item in the gallery section."
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Media item"
        verbose_name_plural = "Media library"

    def __str__(self):
        return self.title

    def clean(self):
        if self.file and self.file.name:
            name = self.file.name.lower()
            size = self.file.size if hasattr(self.file, "size") else 0
            if self.type == self.TYPE_IMAGE:
                if not any(name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                    raise ValidationError({"file": "Images must be jpg, png or webp."})
                if size > 5 * 1024 * 1024:
                    raise ValidationError({"file": "Images must be smaller than 5 MB."})
            elif self.type == self.TYPE_VIDEO:
                if not any(name.endswith(ext) for ext in (".mp4", ".webm")):
                    raise ValidationError({"file": "Videos must be mp4 or webm."})
                if size > 50 * 1024 * 1024:
                    raise ValidationError({"file": "Videos must be smaller than 50 MB."})


class FAQ(models.Model):
    """Frequently asked question for the FAQ section and chatbot."""

    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


# ── Chatbot models ────────────────────────────────────────────────────────────

class BotSettings(models.Model):
    """Singleton: settings for the Mila chat widget."""

    enabled = models.BooleanField(
        default=True, help_text="Show the chat widget on the website."
    )
    bot_name = models.CharField(
        max_length=40, default="Mila",
        help_text="Name shown in the chat header.",
    )
    welcome_message = models.CharField(
        max_length=300,
        default="Hi, I'm Mila! 🌟 I help you find the right toy for your child.\n\nWhat can I help you with?",
        help_text="First message the bot sends when a visitor opens the chat.",
    )
    quick_reply_1 = models.CharField(max_length=60, blank=True, default="🧸 Find a toy")
    quick_reply_2 = models.CharField(max_length=60, blank=True, default="🚚 Delivery & shipping")
    quick_reply_3 = models.CharField(max_length=60, blank=True, default="💳 Payment methods")
    quick_reply_4 = models.CharField(max_length=60, blank=True, default="📦 Track my order")
    quick_reply_5 = models.CharField(max_length=60, blank=True, default="💬 Talk to our team")
    quick_reply_6 = models.CharField(max_length=60, blank=True,
                                     help_text="Optional 6th quick-reply button.")
    fallback_message = models.CharField(
        max_length=300,
        default="I'm not sure about that 🤔 Would you like to ask our team on WhatsApp? They reply within minutes.",
        help_text="Reply sent when the bot can't find an answer.",
    )
    use_ai = models.BooleanField(
        "Use AI answers (needs ANTHROPIC_API_KEY)", default=False,
        help_text="If on and the ANTHROPIC_API_KEY env var is set, the bot will use Claude AI for unknown questions.",
    )

    class Meta:
        verbose_name = "Bot settings"
        verbose_name_plural = "Bot settings"

    def __str__(self):
        return "Bot settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def quick_replies(self):
        return [r for r in [
            self.quick_reply_1, self.quick_reply_2, self.quick_reply_3,
            self.quick_reply_4, self.quick_reply_5, self.quick_reply_6,
        ] if r.strip()]


class BotAnswer(models.Model):
    """Pre-written Q&A pairs for the chatbot keyword engine."""

    question = models.CharField(
        max_length=200,
        help_text="Main question this answer covers, e.g. 'How do I pay?'",
    )
    keywords = models.TextField(
        help_text=(
            "Words or phrases that trigger this answer, one per line.\n"
            "Include key words from the question itself, e.g.:\n"
            "payment\ncod\ncash\npay\nhow to pay"
        ),
    )
    answer = models.TextField(help_text="The reply the bot will send.")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", help_text="Optional: link to a product mentioned in the answer.",
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", help_text="Optional: link to a category mentioned in the answer.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bot answer"
        verbose_name_plural = "Questions & answers"
        ordering = ["question"]

    def __str__(self):
        return self.question

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.splitlines() if k.strip()]


class ChatLog(models.Model):
    """Read-only log of chatbot conversations."""

    session_key = models.CharField(max_length=40, blank=True)
    question = models.TextField()
    answer = models.TextField()
    matched = models.BooleanField(
        default=False,
        help_text="True if a matching answer was found; False if the bot used the fallback.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat log entry"
        verbose_name_plural = "Chat history"

    def __str__(self):
        return f"{self.question[:60]} ({self.created_at:%Y-%m-%d %H:%M})"
