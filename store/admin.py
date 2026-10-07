from django.contrib import admin
from django.utils.html import format_html

from .models import Banner, Category, Need, Product, ProductPhoto, StoreSettings, Testimonial


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Shop", {"fields": ["store_name", "tagline", "announcement", "city"]}),
        ("Contact", {"fields": ["whatsapp_number", "email", "instagram_url", "facebook_url"]}),
        ("Delivery", {"fields": ["delivery_fee", "free_delivery_over"]}),
        ("Payments", {"fields": ["cod_enabled", "jazzcash_number", "easypaisa_number",
                                 "account_title", "bank_details"]}),
    ]

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "short", "color", "order", "is_active", "product_count"]
    fields = ["name", "slug", "short", "color", "image", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}

    @admin.display(description="Toys")
    def product_count(self, obj):
        return obj.products.count()


class PhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1


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
class ProductAdmin(admin.ModelAdmin):
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
        ("Pictures", {"fields": ["image", "illustration"],
                      "description": "Upload a square photo (at least 800×800). Until then the drawing is shown."}),
        ("Visibility", {"fields": [("is_active", "is_featured", "therapist_pick")]}),
    ]

    @admin.display(description="")
    def thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:8px">',
                               obj.image.url)
        return "—"

    @admin.display(description="Stock status")
    def stock_flag(self, obj):
        if obj.stock == 0:
            return format_html('<b style="color:#b42318">Sold out</b>')
        if obj.low_stock:
            return format_html('<b style="color:#b54708">Low</b>')
        return "OK"


@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ["name", "short", "color", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["preview", "title", "link", "order", "is_active"]
    list_display_links = ["preview", "title"]
    list_editable = ["order", "is_active"]
    fieldsets = [
        (None, {"fields": ["title", "subtitle", ("button_text", "link")]}),
        ("Picture", {"fields": ["image", "mobile_image", "image_has_text"],
                     "description": "Make banners in Canva (1600×600). Without a picture, a coloured banner "
                                    "with a toy drawing is shown."}),
        ("Without a picture", {"fields": [("style", "illustration")]}),
        ("Show", {"fields": [("order", "is_active")]}),
    ]

    @admin.display(description="")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:6px">', obj.image.url)
        return obj.get_style_display()


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["name", "rating", "short_text", "product", "is_active", "created_at"]
    list_editable = ["is_active"]
    list_filter = ["is_active", "rating"]
    autocomplete_fields = ["product"]

    @admin.display(description="Message")
    def short_text(self, obj):
        return obj.text[:70]
