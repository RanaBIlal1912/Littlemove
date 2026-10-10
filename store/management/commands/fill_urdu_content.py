"""
Idempotent command: fills empty *_ur fields with natural Urdu translations.
Only writes fields that are currently EMPTY. Never overwrites existing content.
"""
from django.core.management.base import BaseCommand
from store.models import Category, Need, Product, Banner
from store.urdu_content import CATEGORY_UR, NEED_UR, PRODUCT_UR, BANNER_UR


class Command(BaseCommand):
    help = "Fill empty Urdu fields with natural translations (never overwrites)."

    def handle(self, *args, **options):
        updated = 0

        for cat in Category.objects.all():
            data = CATEGORY_UR.get(cat.name)
            if not data:
                continue
            changed = False
            for field, value in data.items():
                if not getattr(cat, field):
                    setattr(cat, field, value)
                    changed = True
            if changed:
                cat.save()
                updated += 1
                self.stdout.write(f"  Category: {cat.name}")

        for need in Need.objects.all():
            data = NEED_UR.get(need.name)
            if not data:
                continue
            changed = False
            for field, value in data.items():
                if not getattr(need, field):
                    setattr(need, field, value)
                    changed = True
            if changed:
                need.save()
                updated += 1
                self.stdout.write(f"  Need: {need.name}")

        for product in Product.objects.all():
            data = PRODUCT_UR.get(product.name)
            if not data:
                continue
            changed = False
            for field, value in data.items():
                if not getattr(product, field):
                    setattr(product, field, value)
                    changed = True
            if changed:
                product.save()
                updated += 1
                self.stdout.write(f"  Product: {product.name}")

        for banner in Banner.objects.all():
            data = BANNER_UR.get(banner.title)
            if not data:
                continue
            changed = False
            for field, value in data.items():
                if not getattr(banner, field):
                    setattr(banner, field, value)
                    changed = True
            if changed:
                banner.save()
                updated += 1
                self.stdout.write(f"  Banner: {banner.title}")

        self.stdout.write(self.style.SUCCESS(
            f"Done — updated {updated} records (never overwrites existing content)."))
