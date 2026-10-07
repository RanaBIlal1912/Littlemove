from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve

from store.sitemaps import ProductSitemap, StaticSitemap

admin.site.site_header = "LittleMove — store manager"
admin.site.site_title = "LittleMove admin"
admin.site.index_title = "Orders, toys and settings"
admin.site.enable_nav_sidebar = False


def robots(request):
    lines = ["User-agent: *", f"Disallow: /{settings.ADMIN_URL}", "Disallow: /cart/",
             "Disallow: /checkout/", "Disallow: /order/",
             f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": {"static": StaticSitemap, "products": ProductSitemap}}),
    path("robots.txt", robots),
    path("", include("orders.urls")),
    path("", include("store.urls")),
]

# Uploaded product photos. On a VPS let Nginx serve /media/ instead.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
