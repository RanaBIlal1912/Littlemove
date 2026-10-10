from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.db.models import Count, Max
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import (
    Banner, BotAnswer, BotSettings, BrandingSettings, Bundle, Category,
    ChatLog, DeliverySettings, FAQ, HomeSection, MediaItem, Need, OurStory,
    PaymentSettings, Popup, Product, ProductPhoto, RoleProfile, RoleProxy,
    StaffProfile, StoreInfo, StoreSettings, Testimonial,
)
from .roles import ROLE_CAPABILITIES, codenames_from_capabilities, permissions_for_codenames


# ── Store settings ─────────────────────────────────────────────────────────────

@admin.register(StoreSettings)
class StoreSettingsAdmin(ModelAdmin):
    tabs = True
    save_on_top = True
    fieldsets = [
        (
            "Contact",
            {
                "fields": [
                    "store_name", "tagline", "city",
                    "whatsapp_number", "email",
                    "instagram_url", "facebook_url", "tiktok_url", "youtube_url",
                ],
                "classes": ["tab"],
                "description": "Your shop name and how customers can reach you.",
            },
        ),
        (
            "Payments",
            {
                "fields": [
                    "cod_enabled",
                    "jazzcash_number", "easypaisa_number",
                    "account_title", "bank_details",
                ],
                "classes": ["tab"],
                "description": (
                    "Cash on delivery is the default. Add JazzCash / EasyPaisa numbers "
                    "to let customers pay online. Leave bank details blank to hide that option."
                ),
            },
        ),
        (
            "Delivery",
            {
                "fields": ["delivery_fee", "free_delivery_over"],
                "classes": ["tab"],
                "description": (
                    "Set the flat delivery fee charged per order. "
                    "Orders at or above the free-delivery amount ship free — set to 0 to never offer free delivery."
                ),
            },
        ),
        (
            "Branding",
            {
                "fields": [
                    "logo", "white_logo", "favicon",
                    ("primary_color", "secondary_color"),
                    ("accent_color", "background_color"),
                    "announcement", "footer_text",
                    "animated_bg", "hero_height",
                    "seo_title", "seo_description", "share_image",
                ],
                "classes": ["tab"],
                "description": (
                    "Upload your logo, pick brand colours, and write the scrolling announcement bar text. "
                    "Separate multiple announcement messages with |"
                ),
            },
        ),
    ]

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = StoreSettings.objects.first()
        if obj:
            return redirect(reverse("admin:store_storesettings_change", args=[obj.pk]))
        return redirect(reverse("admin:store_storesettings_add"))


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


class HasPhotoFilter(admin.SimpleListFilter):
    title = "has photo"
    parameter_name = "has_photo"

    def lookups(self, request, model_admin):
        return [("yes", "Has photo"), ("no", "No photo")]

    def queryset(self, request, qs):
        if self.value() == "yes":
            return qs.exclude(image="")
        if self.value() == "no":
            return qs.filter(image="")
        return qs


class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True


class ProductAdminForm(forms.ModelForm):
    extra_photos = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=False,
        label="Upload more photos",
        help_text="Pick several photos at once — each becomes a new extra photo card below.",
    )

    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "needs": forms.CheckboxSelectMultiple(),
        }

    def clean_extra_photos(self):
        # Actual files are handled in save_related via request.FILES.getlist()
        return None


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductAdminForm
    tabs = True
    save_on_top = True
    change_list_template = "admin/store/product/change_list.html"
    list_display = ["thumb", "name", "category", "price", "stock", "stock_flag",
                    "is_active", "is_featured"]
    list_display_links = ["thumb", "name"]
    list_editable = ["price", "stock", "is_active", "is_featured"]
    list_filter = [StockFilter, HasPhotoFilter, "category", "is_active", "is_featured", "therapist_pick"]
    search_fields = ["name", "sku", "summary"]
    inlines = [PhotoInline]
    list_per_page = 50
    actions = ["show_in_shop", "hide_from_shop"]

    @admin.action(description="Show selected products in shop")
    def show_in_shop(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} product(s) are now visible in the shop.")

    @admin.action(description="Hide selected products from shop")
    def hide_from_shop(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} product(s) are now hidden from the shop.")
    fieldsets = [
        (
            "Basics",
            {
                "fields": [
                    "name", "category", "summary",
                    ("price", "compare_at_price"),
                    ("stock", "age_from", "age_to"),
                    ("is_active", "is_featured", "therapist_pick"),
                ],
                "classes": ["tab"],
            },
        ),
        (
            "Photos",
            {
                "fields": ["image", "extra_photos"],
                "classes": ["tab"],
                "description": (
                    "Upload a square photo (at least 800×800 px). "
                    "The drawing below is shown until you upload a real photo. "
                    "Use 'Upload more photos' to add extra photos all at once."
                ),
            },
        ),
        (
            "Details",
            {
                "fields": ["description", "helps_with", "in_the_box", "needs"],
                "classes": ["tab"],
            },
        ),
        (
            "Advanced",
            {
                "fields": ["slug", "sku", "illustration"],
                "classes": ["tab"],
                "description": "The slug is the URL-friendly name. It auto-fills from the product name.",
            },
        ),
    ]
    prepopulated_fields = {"slug": ["name"]}

    # Therapist Reviewer: has change_product but not add_product.
    THERAPIST_ALLOWED = frozenset([
        "description", "helps_with", "in_the_box",
        "therapist_pick", "age_from", "age_to", "summary",
    ])

    @staticmethod
    def _is_therapist(request):
        return (
            not request.user.is_superuser
            and request.user.has_perm("store.change_product")
            and not request.user.has_perm("store.add_product")
        )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if self._is_therapist(request) and obj:
            all_fields = {f.name for f in Product._meta.get_fields()
                          if not f.many_to_many and not f.one_to_many}
            ro.extend(all_fields - self.THERAPIST_ALLOWED - {"id"})
        return ro

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self._is_therapist(request):
            for field_name in list(form.base_fields.keys()):
                if field_name not in self.THERAPIST_ALLOWED:
                    del form.base_fields[field_name]
        return form

    class Media:
        js = ["admin/js/product_price_preview.js"]

    @display(description="")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:8px">',
                obj.image.url,
            )
        return format_html(
            '<span style="display:inline-block;width:48px;height:48px;border-radius:8px;'
            'background:#fef3c7;color:#92400e;font-size:.6rem;font-weight:700;'
            'display:inline-flex;align-items:center;justify-content:center;text-align:center;'
            'line-height:1.2">No<br>photo</span>'
        )

    @display(description="Stock status")
    def stock_flag(self, obj):
        if obj.stock == 0:
            return format_html('<b style="color:#b42318">Sold out</b>')
        if obj.low_stock:
            return format_html('<b style="color:#b54708">Low</b>')
        return "OK"

    def get_urls(self):
        from django.urls import path as urlpath
        custom = [
            urlpath(
                "bulk-upload/",
                self.admin_site.admin_view(self.bulk_upload_view),
                name="store_product_bulk_upload",
            ),
            urlpath(
                "bulk-import/",
                self.admin_site.admin_view(self.bulk_import_view),
                name="store_product_bulk_import",
            ),
        ]
        return custom + super().get_urls()

    def bulk_upload_view(self, request):
        import os
        from django.conf import settings as djsettings
        from django.shortcuts import render
        from .bulk_upload import MAX_ZIP_BYTES, process_bulk_zip

        cloudinary_warning = (
            not os.environ.get("CLOUDINARY_URL") and not djsettings.DEBUG
        )
        report = None
        error = None

        if request.method == "POST":
            zf = request.FILES.get("zipfile")
            if not zf:
                error = "Please choose a ZIP file."
            elif zf.size > MAX_ZIP_BYTES:
                mb = zf.size // (1024 * 1024)
                error = f"ZIP file must be ≤ 60 MB (yours is {mb} MB)."
            else:
                replace = request.POST.get("replace") == "on"
                report = process_bulk_zip(zf.read(), replace=replace)

        context = {
            **self.admin_site.each_context(request),
            "title": "Bulk photo upload",
            "opts": self.model._meta,
            "cloudinary_warning": cloudinary_warning,
            "report": report,
            "error": error,
        }
        return render(request, "store/admin_bulk_upload.html", context)

    def bulk_import_view(self, request):
        import os
        import tempfile
        from django.conf import settings as djsettings
        from django.shortcuts import render
        from .bulk_import import (
            MAX_ROWS, build_preview, execute_import, match_photos_zip,
        )
        from .bulk_upload import MAX_ZIP_BYTES, process_bulk_zip

        cloudinary_warning = (
            not os.environ.get("CLOUDINARY_URL") and not djsettings.DEBUG
        )
        step = "form"
        preview = None
        result = None
        error = None
        session_options = {}

        if request.method == "POST":
            action = request.POST.get("action", "preview")

            if action == "preview":
                import_file = request.FILES.get("import_file")
                zip_file = request.FILES.get("photos_zip")
                create_missing = request.POST.get("create_missing_categories") == "on"
                import_as_hidden = request.POST.get("import_as_hidden") == "on"
                replace_photos = request.POST.get("replace_photos") == "on"

                if not import_file:
                    error = "Please choose a spreadsheet file (.xlsx or .csv)."
                else:
                    file_bytes = import_file.read()
                    filename = import_file.name

                    # Save xlsx/csv to temp file
                    suffix = os.path.splitext(filename)[1] or ".xlsx"
                    fd, tmp_xlsx = tempfile.mkstemp(suffix=suffix)
                    os.close(fd)
                    with open(tmp_xlsx, "wb") as fh:
                        fh.write(file_bytes)

                    # Save photos ZIP to temp file (if provided and within size limit)
                    tmp_zip = None
                    if zip_file:
                        if zip_file.size > MAX_ZIP_BYTES:
                            mb = zip_file.size // (1024 * 1024)
                            error = (
                                f"Photos ZIP is too large ({mb} MB, max 60 MB). "
                                "Upload photos separately using Bulk photo upload."
                            )
                        else:
                            fd2, tmp_zip = tempfile.mkstemp(suffix=".zip")
                            os.close(fd2)
                            with open(tmp_zip, "wb") as fh:
                                fh.write(zip_file.read())

                    if not error:
                        request.session["_bulk_import"] = {
                            "file_path": tmp_xlsx,
                            "filename": filename,
                            "zip_path": tmp_zip,
                            "options": {
                                "create_missing_categories": create_missing,
                                "import_as_hidden": import_as_hidden,
                                "replace_photos": replace_photos,
                            },
                        }
                        try:
                            preview = build_preview(
                                file_bytes, filename,
                                create_missing, import_as_hidden,
                            )
                            session_options = request.session["_bulk_import"]["options"]
                            step = "preview"
                        except Exception as exc:
                            for p in [tmp_xlsx, tmp_zip]:
                                if p:
                                    try:
                                        os.unlink(p)
                                    except OSError:
                                        pass
                            request.session.pop("_bulk_import", None)
                            error = f"Could not read file: {exc}"

            elif action == "confirm":
                session_data = request.session.pop("_bulk_import", None)
                if not session_data:
                    error = "Session expired — please upload the file again."
                else:
                    tmp_xlsx = session_data.get("file_path")
                    filename = session_data.get("filename", "import.xlsx")
                    tmp_zip = session_data.get("zip_path")
                    options = session_data.get("options", {})

                    try:
                        with open(tmp_xlsx, "rb") as fh:
                            file_bytes = fh.read()
                    except (IOError, TypeError):
                        file_bytes = None
                        error = "Temporary file not found — please upload again."

                    if file_bytes:
                        import_result = execute_import(file_bytes, filename, options)
                        photo_result = None

                        if tmp_zip:
                            try:
                                with open(tmp_zip, "rb") as fh:
                                    zip_bytes = fh.read()
                                image_file_map = import_result.get("image_file_map", {})
                                if image_file_map:
                                    photo_result = match_photos_zip(
                                        zip_bytes, image_file_map,
                                        replace_existing=options.get("replace_photos", False),
                                    )
                                else:
                                    photo_result = process_bulk_zip(
                                        zip_bytes,
                                        replace=options.get("replace_photos", False),
                                    )
                            except Exception as exc:
                                import_result["errors"].append(f"Photo import error: {exc}")

                        result = {
                            "created": import_result["created"],
                            "updated": import_result["updated"],
                            "errors": import_result["errors"],
                            "photo_result": photo_result,
                        }
                        step = "result"

                    # Clean up temp files
                    for p in [tmp_xlsx, tmp_zip]:
                        if p:
                            try:
                                os.unlink(p)
                            except OSError:
                                pass

            elif action == "cancel":
                session_data = request.session.pop("_bulk_import", None)
                if session_data:
                    for p in [session_data.get("file_path"), session_data.get("zip_path")]:
                        if p:
                            try:
                                os.unlink(p)
                            except OSError:
                                pass

        context = {
            **self.admin_site.each_context(request),
            "title": "Bulk product import",
            "opts": self.model._meta,
            "cloudinary_warning": cloudinary_warning,
            "MAX_ROWS": MAX_ROWS,
            "step": step,
            "preview": preview,
            "session_options": session_options,
            "result": result,
            "error": error,
        }
        return render(request, "store/admin_bulk_import.html", context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        files = request.FILES.getlist("extra_photos")
        if files:
            obj = form.instance
            max_order = ProductPhoto.objects.filter(product=obj).aggregate(m=Max("order"))["m"] or 0
            for i, f in enumerate(files):
                ProductPhoto.objects.create(product=obj, image=f, order=max_order + i + 1)


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
        ("Fallback & AI", {"fields": ["fallback_message", "use_ai"]}),
    ]

    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class BotAnswerAdminForm(forms.ModelForm):
    class Meta:
        model = BotAnswer
        fields = "__all__"

    def clean_show_as_quick(self):
        val = self.cleaned_data.get("show_as_quick")
        if val:
            qs = BotAnswer.objects.filter(show_as_quick=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.count() >= 6:
                raise forms.ValidationError(
                    "Only 6 quick buttons can be shown. Untick one first."
                )
        return val


@admin.register(BotAnswer)
class BotAnswerAdmin(ModelAdmin):
    form = BotAnswerAdminForm
    change_list_template = "admin/store/botanswer/change_list.html"
    list_display = ["question", "show_as_quick", "active", "short_answer"]
    list_editable = ["active", "show_as_quick"]
    list_filter = ["active", "show_as_quick"]
    search_fields = ["question", "keywords", "answer"]
    autocomplete_fields = ["product", "category"]
    fieldsets = [
        (None, {
            "fields": ["question", "keywords", "answer", "product", "category", "active"],
        }),
        ("Quick button", {
            "fields": ["show_as_quick", "quick_label", "quick_order", "action"],
            "description": "Show this Q&A as a chip in the chat widget (max 6 total).",
        }),
    ]

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["quick_used"] = BotAnswer.objects.filter(show_as_quick=True).count()
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        if obj.show_as_quick:
            qs = BotAnswer.objects.filter(show_as_quick=True)
            if obj.pk:
                qs = qs.exclude(pk=obj.pk)
            if qs.count() >= 6:
                self.message_user(
                    request,
                    "Only 6 quick buttons can be shown. Untick one first.",
                    level="ERROR",
                )
                obj.show_as_quick = False
        super().save_model(request, obj, form, change)

    @display(description="Quick")
    def quick_badge(self, obj):
        if obj.show_as_quick:
            return format_html(
                '<span style="color:#067647;font-weight:700;font-size:1.1em">&#10003;</span>'
            )
        return "—"

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


# ── Proxy settings pages ───────────────────────────────────────────────────────

class _SingletonProxyAdmin(ModelAdmin):
    """Each proxy settings page redirects to the one StoreSettings row."""
    save_on_top = True

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        obj = StoreSettings.objects.first()
        mn = self.model._meta.model_name
        al = self.model._meta.app_label
        if obj:
            return redirect(reverse(f"admin:{al}_{mn}_change", args=[obj.pk]))
        return redirect(reverse("admin:store_storesettings_add"))


@admin.register(StoreInfo)
class StoreInfoAdmin(_SingletonProxyAdmin):
    fieldsets = [(None, {"fields": [
        "store_name", "tagline", "city",
        "whatsapp_number", "email",
        "instagram_url", "facebook_url", "tiktok_url", "youtube_url",
    ], "description": "Your shop name and how customers can reach you."})]


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(_SingletonProxyAdmin):
    fieldsets = [(None, {"fields": [
        "cod_enabled", "jazzcash_number", "easypaisa_number",
        "account_title", "bank_details",
    ], "description": "Cash on delivery is the default. Add JazzCash / EasyPaisa numbers to let customers pay online."})]


@admin.register(DeliverySettings)
class DeliverySettingsAdmin(_SingletonProxyAdmin):
    fieldsets = [(None, {"fields": [
        "delivery_fee", "free_delivery_over",
    ], "description": "Flat delivery fee per order. Set free_delivery_over to 0 to never offer free delivery."})]


@admin.register(BrandingSettings)
class BrandingSettingsAdmin(_SingletonProxyAdmin):
    fieldsets = [(None, {"fields": [
        "logo", "white_logo", "favicon",
        ("primary_color", "secondary_color"),
        ("accent_color", "background_color"),
        "announcement", "footer_text",
        "animated_bg", "hero_height",
        "seo_title", "seo_description", "share_image",
    ], "description": "Upload your logo, pick brand colours, and write the announcement bar. Separate messages with |"})]


# ── Roles ──────────────────────────────────────────────────────────────────────

admin.site.unregister(Group)


class RoleCapabilityForm(forms.ModelForm):
    """Replaces raw Permission m2m with plain-English capability checkboxes."""

    class Meta:
        model = RoleProxy
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = set()
        if self.instance and self.instance.pk:
            current = {
                f"{al}.{cn}"
                for al, cn in self.instance.permissions.values_list(
                    "content_type__app_label", "codename"
                )
            }
        for _gk, _gl, caps in ROLE_CAPABILITIES:
            for cap_key, cap_label, perm_list in caps:
                initial = bool(set(perm_list).issubset(current)) if current else False
                self.fields[cap_key] = forms.BooleanField(
                    label=cap_label, required=False, initial=initial,
                )

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            selected = [
                key
                for _gk, _gl, caps in ROLE_CAPABILITIES
                for key, _label, _perms in caps
                if self.cleaned_data.get(key)
            ]
            group.permissions.set(
                permissions_for_codenames(codenames_from_capabilities(selected))
            )
            RoleProfile.objects.get_or_create(group=group, defaults={"is_default": False})
        return group


@admin.register(RoleProxy)
class RolesAdmin(ModelAdmin):
    form = RoleCapabilityForm
    list_display = ["name", "role_description", "user_count", "type_badge"]
    search_fields = ["name"]

    def get_fieldsets(self, request, obj=None):
        fs = [(None, {"fields": ["name"]})]
        for _gk, group_label, caps in ROLE_CAPABILITIES:
            fs.append((group_label, {"fields": [k for k, _, _ in caps]}))
        return fs

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        if obj is None:
            return True
        try:
            return not obj.profile.is_default
        except Exception:
            return True

    @display(description="Description")
    def role_description(self, obj):
        try:
            return obj.profile.description
        except Exception:
            return "—"

    @display(description="Users")
    def user_count(self, obj):
        return obj.user_set.count()

    @display(description="Type")
    def type_badge(self, obj):
        try:
            if obj.profile.is_default:
                return format_html(
                    '<span style="color:#1d4ed8;font-weight:600">Built-in</span>'
                )
        except Exception:
            pass
        return format_html('<span style="color:#667085">Custom</span>')


# ── Staff users ────────────────────────────────────────────────────────────────

class StaffProfileForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput, required=False,
        help_text="Required for new staff. Leave blank to keep the existing password.",
    )
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput, required=False,
    )
    role = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        widget=forms.RadioSelect,
        required=False,
        empty_label="No role assigned",
        help_text="Assign exactly one role.",
    )

    class Meta:
        model = StaffProfile
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Group.objects.all()
        if self.instance.pk:
            g = self.instance.groups.first()
            if g:
                self.fields["role"].initial = g

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Passwords don't match.")
        if not self.instance.pk and not p1:
            self.add_error("password1", "Password is required for new staff members.")
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        p = self.cleaned_data.get("password1")
        if p:
            user.set_password(p)
        if commit:
            user.save()
            role = self.cleaned_data.get("role")
            user.groups.set([role] if role else [])
        return user


@admin.register(StaffProfile)
class StaffProfileAdmin(ModelAdmin):
    form = StaffProfileForm
    list_display = ["username", "full_name_col", "email", "staff_role", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]
    fieldsets = [
        (None, {"fields": ["username", ("first_name", "last_name"), "email", "is_active"]}),
        ("Password", {"fields": ["password1", "password2"]}),
        ("Role", {
            "fields": ["role"],
            "description": "Assign exactly one role to determine what this staff member can access.",
        }),
    ]

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=False)

    @display(description="Full name")
    def full_name_col(self, obj):
        return obj.get_full_name() or "—"

    @display(description="Role")
    def staff_role(self, obj):
        g = obj.groups.first()
        return g.name if g else format_html('<span style="color:#667085">—</span>')
