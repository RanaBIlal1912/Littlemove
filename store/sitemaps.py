from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Product


class StaticSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return ["store:home", "store:shop", "store:gallery", "store:delivery"]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return Product.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    """Skill category pages (only ones that actually list toys)."""
    changefreq = "weekly"

    def items(self):
        return Category.objects.with_toys()
