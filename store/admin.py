from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import (
    Banner, BotAnswer, BotSettings, Bundle, Category, ChatLog, FAQ,
    HomeSection, MediaItem, Need, OurStory, Popup, Product, ProductPhoto,
    StoreSettings, Testimonial,
)


# ── Store settings ─────────────────────────────────────────────────────────────

@admin.register(StoreSettings)
class StoreSettingsAdmin(ModelAdmin):
    fieldsets = [
        ("Shop", {"fields": ["store_name", "tagline", "announcement", "city"]}),
        ("Homepage design", {"fields": ["animated_bg", "hero_height"]}),
        ("Branding & colours", {"fields": [
            "logo", "white_logo", "favicon",
            ("primary_color", "secondary_color"),
            ("accent_color", "background_color"),
        ]}),
        ("Contact & social", {"fields": [
            "whatsapp_number", "email",
            "instagram_url", "facebook_url", "tiktok_url", "youtube_url",
        ]}),
        ("Footer & SEO", {"fields": [
            "footer_text", "seo_title", "seo_description", "share_image",
        ]}),
        ("Delivery", {"fields": ["delivery_fee", "free_delivery_over"]}),
        ("Payments", {"fields": [
            "cod_enabled", "jazzcash_number", "easypaisa_number",
            "account_title", "bank_details",
        ]}),
    ]

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ── Categories & needs ─────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "short", "color", "order", "is_active", "product_count"]
    fields = ["name", "slug", "short", "color", "image", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]

    @display(description="Toys")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Need)
class NeedAdmin(ModelAdmin):
    list_display = ["name", "short", "color", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]


# ── Products ───────────────────────────────────────────────────────────────────

class PhotoInline(TabularInline):
    model = ProductPhoto
    extra = 1
    fields = ["image", "alt", "order"]


class StockFilter(admin.SimpleListFilter):
    title = "stock"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return [("out", "Sold out"), ("low", "Low (3 or less)"), ("ok", "In stock")]

    def queryset(self, request, qs):
        if self.value() == "out":
            return qs.filter(stock=0)
        if self.value() == "low":
            return qs.filter(stock__gt=0, stock__lte=3)
        if self.value() == "ok":
            return qs.filter(stock__gt=3)
        return qs


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ["thumb", "name", "category", "price", "stock", "stock_flag",
                    "is_active", "is_featured"]
    list_display_links = ["thumb", "name"]
    list_editable = ["price", "stock", "is_active", "is_featured"]
    list_filter = [StockFilter, "category", "is_active", "is_featured", "therapist_pick"]
    search_fields = ["name", "sku", "summary"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [PhotoInline]
    filter_horizontal = ["needs"]
    list_per_page = 50
    fieldsets = [
        (None, {"fields": ["name", "slug", "category", "needs", "summary"]}),
        ("Price and stock", {"fields": [("price", "compare_at_price"), ("stock", "sku")]}),
        ("Age", {"fields": [("age_from", "age_to")]}),
        ("Details", {"fields": ["description", "helps_with", "in_the_box"]}),
        ("Pictures", {
            "fields": ["image", "illustration"],
            "description": "Upload a square photo (at least 800×800). Until then the drawing is shown.",
        }),
        ("Visibility", {"fields": [("is_active", "is_featured", "therapist_pick")]}),
    ]

    @display(description="")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:8px">',
                obj.image.url,
            )
        return "—"

    @display(description="Stock status")
    def stock_flag(self, obj):
        if obj.stock == 0:
            return format_html('<b style="color:#b42318">Sold out</b>')
        if obj.low_stock:
            return format_html('<b style="color:#b54708">Low</b>')
        return "OK"


# ── Banners ────────────────────────────────────────────────────────────────────

@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ["preview", "title", "link", "order", "is_active"]
    list_display_links = ["preview", "title"]
    list_editable = ["order", "is_active"]
    search_fields = ["title"]
    fieldsets = [
        (None, {"fields": ["title", "subtitle", ("button_text", "link")]}),
        ("Picture / Video", {
            "fields": ["image", "mobile_image", "image_has_text", "video"],
            "description": "Make banners in Canva (1600×600). Without a picture, a coloured banner "
                           "with a toy drawing is shown.",
        }),
        ("Without a picture", {"fields": [("style", "illustration")]}),
        ("Show", {"fields": [("order", "is_active")]}),
    ]

    @display(description="")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px">', obj.image.url
            )
        return obj.get_style_display()


# ── Testimonials ───────────────────────────────────────────────────────────────

@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ["name", "rating", "short_text", "product", "is_active", "created_at"]
    list_editable = ["is_active"]
    list_filter = ["is_active", "rating"]
    autocomplete_fields = ["product"]
    search_fields = ["name", "text"]

    @display(description="Message")
    def short_text(self, obj):
        return obj.text[:70]


# ── Home sections ──────────────────────────────────────────────────────────────

@admin.register(HomeSection)
class HomeSectionAdmin(ModelAdmin):
    list_display = ["get_type_display", "title", "enabled", "order"]
    list_editable = ["enabled", "order"]
    list_display_links = ["get_type_display"]
    fields = ["type", "title", "subtitle", "enabled", "order", "bg_image"]
    readonly_fields = ["type"]

    def has_add_permission(self, request):
        return False  # rows are created via data migration

    def has_delete_permission(self, request, obj=None):
        return False


# ── Popups ─────────────────────────────────────────────────────────────────────

@admin.register(Popup)
class PopupAdmin(ModelAdmin):
    list_display = ["name", "title", "active", "where", "start_at", "end_at", "popup_status"]
    list_editable = ["active"]
    list_filter = ["active", "where"]
    search_fields = ["name", "title"]
    fieldsets = [
        (None, {"fields": ["name", "title", "text", "image"]}),
        ("Button", {"fields": [("button_text", "button_link"), "coupon_code"]}),
        ("Timing", {"fields": [("start_at", "end_at"), "delay_seconds", "show_again_days"]}),
        ("Display", {"fields": ["where", "active"]}),
    ]

    @display(description="Status")
    def popup_status(self, obj):
        from django.utils import timezone
        now = timezone.now()
        if not obj.active:
            return format_html('<span style="color:#667085">Off</span>')
        if obj.start_at and obj.start_at > now:
            return format_html('<span style="color:#b54708">Scheduled</span>')
        if obj.end_at and obj.end_at < now:
            return format_html('<span style="color:#b42318">Expired</span>')
        return format_html('<span style="color:#067647">Live</span>')


# ── Media library ──────────────────────────────────────────────────────────────

@admin.register(MediaItem)
class MediaItemAdmin(ModelAdmin):
    list_display = ["thumb", "title", "type", "show_in_gallery", "order"]
    list_display_links = ["thumb", "title"]
    list_editable = ["show_in_gallery", "order"]
    list_filter = ["type", "show_in_gallery"]
    search_fields = ["title", "alt_text"]
    fields = ["title", "type", "file", "youtube_url", "alt_text", "show_in_gallery", "order"]

    @display(description="")
    def thumb(self, obj):
        if obj.file and obj.type == MediaItem.TYPE_IMAGE:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:6px">',
                obj.file.url,
            )
        if obj.type == MediaItem.TYPE_VIDEO:
            return format_html('<span style="font-size:1.5em">🎬</span>')
        if obj.type == MediaItem.TYPE_YOUTUBE:
            return format_html('<span style="font-size:1.5em">▶️</span>')
        return "—"


# ── FAQ ────────────────────────────────────────────────────────────────────────

@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ["question", "active", "order"]
    list_editable = ["active", "order"]
    search_fields = ["question", "answer"]
    fields = ["question", "answer", "order", "active"]


# ── Bundles ────────────────────────────────────────────────────────────────────

@admin.register(Bundle)
class BundleAdmin(ModelAdmin):
    list_display = ["name", "bundle_price_display", "product_count", "active", "created_at"]
    list_editable = ["active"]
    filter_horizontal = ["products"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name", "description"]
    fields = ["name", "slug", "description", "products", "bundle_price", "image", "active"]

    @display(description="Bundle price")
    def bundle_price_display(self, obj):
        return f"Rs {obj.bundle_price:,}"

    @display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


# ── Our story ──────────────────────────────────────────────────────────────────

@admin.register(OurStory)
class OurStoryAdmin(ModelAdmin):
    fields = ["title", "body", "photo", "active"]

    def has_add_permission(self, request):
        return not OurStory.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ── Chatbot ────────────────────────────────────────────────────────────────────

@admin.register(BotSettings)
class BotSettingsAdmin(ModelAdmin):
    fieldsets = [
        ("General", {"fields": ["enabled", "bot_name", "welcome_message"]}),
        ("Quick-reply buttons", {"fields": [
            "quick_reply_1", "quick_reply_2", "quick_reply_3",
            "quick_reply_4", "quick_reply_5", "quick_reply_6",
        ]}),
        ("Fallback & AI", {"fields": ["fallback_message", "use_ai"]}),
    ]

    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BotAnswer)
class BotAnswerAdmin(ModelAdmin):
    list_display = ["question", "active", "short_answer"]
    list_editable = ["active"]
    list_filter = ["active"]
    search_fields = ["question", "keywords", "answer"]
    autocomplete_fields = ["product", "category"]
    fields = ["question", "keywords", "answer", "product", "category", "active"]

    @display(description="Answer preview")
    def short_answer(self, obj):
        return obj.answer[:80]


class UnmatchedFilter(admin.SimpleListFilter):
    title = "matched"
    parameter_name = "matched"

    def lookups(self, request, model_admin):
        return [("no", "Unanswered (bot used fallback)"), ("yes", "Matched")]

    def queryset(self, request, qs):
        if self.value() == "no":
            return qs.filter(matched=False)
        if self.value() == "yes":
            return qs.filter(matched=True)
        return qs


@admin.register(ChatLog)
class ChatLogAdmin(ModelAdmin):
    list_display = ["short_question", "short_answer", "matched", "created_at"]
    list_filter = [UnmatchedFilter, "created_at"]
    search_fields = ["question", "answer"]
    readonly_fields = ["session_key", "question", "answer", "matched", "created_at"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description="Question")
    def short_question(self, obj):
        return obj.question[:70]

    @display(description="Bot answer")
    def short_answer(self, obj):
        return obj.answer[:70]
