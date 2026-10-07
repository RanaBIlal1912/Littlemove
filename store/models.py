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
        default="Free delivery on orders over Rs 5,000 | Cash on delivery all over Pakistan | Toys chosen with therapists",
        help_text="Top bar messages. Separate several with | and they rotate.",
    )
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

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
