"""
LittleMove store settings.

Everything secret or environment-specific comes from environment variables
(or a local .env file). Defaults are safe for local development only.
"""
import os
from pathlib import Path

import dj_database_url
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Tiny .env reader so the project needs no extra package."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise RuntimeError("SECRET_KEY must be set when DEBUG is off.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    # unfold must be before django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "store",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.store",
                "store.context_processors.site_context",
                "store.context_processors.lang_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default (zero setup). Set DATABASE_URL for PostgreSQL/MySQL.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

USE_I18N = False
LANGUAGE_CODE = "en"

ENABLE_GOOGLE_TRANSLATE = env_bool("ENABLE_GOOGLE_TRANSLATE", True)

# ── Content Security Policy (if used) ─────────────────────────────────────────
# When ENABLE_GOOGLE_TRANSLATE is True, allow these external origins:
# script-src: translate.googleapis.com
# style-src:  translate.googleapis.com fonts.googleapis.com
# img-src:    www.gstatic.com translate.googleapis.com
# connect-src: translate.googleapis.com translate.google.com
# font-src:   fonts.gstatic.com
# Add these only to your CSP header if you configure one.
TIME_ZONE = "Asia/Karachi"
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cart lives in the session for 30 days.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
CART_SESSION_KEY = "cart"

# Uploaded product photos: keep them reasonable.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Optional order-alert email (leave EMAIL_HOST empty to skip).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@littlemove.pk")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
ORDER_ALERT_EMAIL = os.environ.get("ORDER_ALERT_EMAIL", "")

# The admin lives at a non-obvious path to cut down on bot noise.
ADMIN_URL = os.environ.get("ADMIN_URL", "manage-store/").strip("/") + "/"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

# ── Render automatic hostname registration ────────────────────────────────────
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")

# ── Cloudinary media storage (set CLOUDINARY_URL env var on Render) ───────────
if os.environ.get("CLOUDINARY_URL"):
    INSTALLED_APPS = list(INSTALLED_APPS) + ["cloudinary_storage", "cloudinary"]
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"
    }

# ── django-unfold admin configuration ─────────────────────────────────────────

UNFOLD = {
    "SITE_TITLE": "LittleMove",
    "SITE_HEADER": "LittleMove",
    "SITE_SUBHEADER": "Store Manager",
    "SITE_URL": "/",
    "SITE_LOGO": lambda request: static("img/littlemove-logo.png"),
    "SITE_ICON": lambda request: static("img/icon-192.png"),
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,

    # Dashboard context callback
    "DASHBOARD_CALLBACK": "store.admin_callbacks.dashboard_callback",

    # Brand colours (blue #3BA4E6 palette to match LittleMove primary)
    "COLORS": {
        "primary": {
            "50":  "oklch(97.5% .012 240)",
            "100": "oklch(94.2% .030 240)",
            "200": "oklch(89.8% .058 240)",
            "300": "oklch(82.5% .107 240)",
            "400": "oklch(71.0% .155 240)",
            "500": "oklch(61% .175 240)",
            "600": "oklch(52% .180 240)",
            "700": "oklch(43.5% .165 240)",
            "800": "oklch(37% .140 240)",
            "900": "oklch(30% .110 240)",
            "950": "oklch(22% .085 240)",
        },
    },

    # Sidebar navigation
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": "Orders",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "New orders",
                        "icon": "fiber_new",
                        "link": lambda request: reverse_lazy("admin:orders_order_changelist").__str__() + "?status=pending",
                        "badge": "store.admin_callbacks.badge_pending_orders",
                        "permission": lambda request: request.user.has_perm("orders.view_order"),
                    },
                    {
                        "title": "All orders",
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                        "permission": lambda request: request.user.has_perm("orders.view_order"),
                    },
                ],
            },
            {
                "title": "Products",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "All products",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:store_product_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_product"),
                    },
                    {
                        "title": "Add product",
                        "icon": "add_box",
                        "link": reverse_lazy("admin:store_product_add"),
                        "permission": lambda request: request.user.has_perm("store.add_product"),
                    },
                    {
                        "title": "Bulk photo upload",
                        "icon": "upload",
                        "link": reverse_lazy("admin:store_product_bulk_upload"),
                        "permission": lambda request: request.user.has_perm("store.add_productphoto"),
                    },
                    {
                        "title": "Bulk product import",
                        "icon": "table_view",
                        "link": reverse_lazy("admin:store_product_bulk_import"),
                        "permission": lambda request: request.user.has_perm("store.add_product"),
                    },
                    {
                        "title": "Low stock",
                        "icon": "warning",
                        "link": lambda request: reverse_lazy("admin:store_product_changelist").__str__() + "?stock=low",
                        "badge": "store.admin_callbacks.badge_low_stock",
                        "permission": lambda request: request.user.has_perm("store.view_product"),
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": reverse_lazy("admin:store_category_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_category"),
                    },
                    {
                        "title": "Shop by need",
                        "icon": "favorite",
                        "link": reverse_lazy("admin:store_need_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_need"),
                    },
                ],
            },
            {
                "title": "Website",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Home sections",
                        "icon": "home",
                        "link": reverse_lazy("admin:store_homesection_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_homesection"),
                    },
                    {
                        "title": "Banners",
                        "icon": "image",
                        "link": reverse_lazy("admin:store_banner_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_banner"),
                    },
                    {
                        "title": "Popup",
                        "icon": "campaign",
                        "link": reverse_lazy("admin:store_popup_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_popup"),
                    },
                    {
                        "title": "Gallery",
                        "icon": "photo_library",
                        "link": reverse_lazy("admin:store_mediaitem_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_mediaitem"),
                    },
                    {
                        "title": "Testimonials",
                        "icon": "star",
                        "link": reverse_lazy("admin:store_testimonial_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_testimonial"),
                    },
                    {
                        "title": "FAQ",
                        "icon": "quiz",
                        "link": reverse_lazy("admin:store_faq_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_faq"),
                    },
                ],
            },
            {
                "title": "Chatbot",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Questions & answers",
                        "icon": "question_answer",
                        "link": reverse_lazy("admin:store_botanswer_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_botanswer"),
                    },
                    {
                        "title": "Bot settings",
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:store_botsettings_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_botsettings"),
                    },
                    {
                        "title": "Chat history",
                        "icon": "history",
                        "link": reverse_lazy("admin:store_chatlog_changelist"),
                        "permission": lambda request: request.user.has_perm("store.view_chatlog"),
                    },
                ],
            },
            {
                "title": "Settings",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Store info",
                        "icon": "store",
                        "link": reverse_lazy("admin:store_storeinfo_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Payments",
                        "icon": "payments",
                        "link": reverse_lazy("admin:store_paymentsettings_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Delivery",
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:store_deliverysettings_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Branding",
                        "icon": "palette",
                        "link": reverse_lazy("admin:store_brandingsettings_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Roles",
                        "icon": "groups",
                        "link": reverse_lazy("admin:store_roleproxy_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": "Staff users",
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:store_staffprofile_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Let Django serve uploaded photos itself (fine for a small shop on PythonAnywhere
# or a single small server). Turn off if Nginx/your host serves /media/.
SERVE_MEDIA = env_bool("SERVE_MEDIA", True)
