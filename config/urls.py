from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from django.templatetags.static import static

from store.sitemaps import CategorySitemap, ProductSitemap, StaticSitemap

admin.site.site_header = "LittleMove — store manager"
admin.site.site_title = "LittleMove admin"
admin.site.index_title = "Orders, toys and settings"


def robots(request):
    # The admin path is deliberately not listed: robots.txt is public and would
    # reveal the secret ADMIN_URL. The admin login page is noindex anyway.
    lines = ["User-agent: *", "Disallow: /cart/",
             "Disallow: /checkout/", "Disallow: /order/", "Disallow: /track/",
             f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def web_manifest(request):
    """Lets phones offer 'Add to home screen' with the LittleMove icon."""
    import json
    data = {
        "name": "LittleMove", "short_name": "LittleMove", "start_url": "/", "display": "standalone",
        "background_color": "#FFF9F0", "theme_color": "#3BA4E6",
        "icons": [
            {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        ],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


urlpatterns = [
    # Browsers ask for /favicon.ico regardless of the <link> tag.
    path("favicon.ico", RedirectView.as_view(url=static("img/favicon.ico"), permanent=True)),
    path("manifest.webmanifest", web_manifest),
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": {"static": StaticSitemap, "categories": CategorySitemap, "products": ProductSitemap}}),
    path("robots.txt", robots),
    path("", include("orders.urls")),
    path("", include("store.urls")),
]

# Uploaded product photos. On a VPS let Nginx serve /media/ instead.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
