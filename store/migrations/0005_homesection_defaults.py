"""Data migration: create default HomeSection rows in the canonical order."""
from django.db import migrations


DEFAULT_SECTIONS = [
    ("hero_slider",       "Hero slider (banners)",            0),
    ("trust_badges",      "Trust badges",                     1),
    ("shop_by_skill",     "Shop by skill",                    2),
    ("shop_by_need",      "Shop by need",                     3),
    ("featured_products", "Featured products",                4),
    ("shop_by_age",       "Shop by age",                      5),
    ("sale_products",     "Sale products",                    6),
    ("promo_banners",     "Promo banners",                    7),
    ("new_arrivals",      "New arrivals",                     8),
    ("shop_by_budget",    "Shop by budget",                   9),
    ("therapist_picks",   "Therapist picks",                  10),
    ("testimonials",      "What parents say (testimonials)", 11),
    ("whatsapp_help",     "WhatsApp help band",               12),
    ("faq",               "FAQ / Questions parents ask",      13),
]


def create_defaults(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    for section_type, _, order in DEFAULT_SECTIONS:
        HomeSection.objects.get_or_create(type=section_type, defaults={"order": order, "enabled": True})


def remove_defaults(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    HomeSection.objects.filter(type__in=[t for t, _, _ in DEFAULT_SECTIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_storesettings_branding_new_models"),
    ]

    operations = [
        migrations.RunPython(create_defaults, reverse_code=remove_defaults),
    ]
