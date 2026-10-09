"""Migration 0009: add why_us + final_cta HomeSection types; reorder needs before skills."""
from django.db import migrations, models


NEW_SECTIONS = [
    ("why_us",    "Why parents choose LittleMove", 17),
    ("final_cta", "Final CTA (Ready to find their favourite?)", 18),
]


def add_sections_and_reorder(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    # Add new sections
    for section_type, _, order in NEW_SECTIONS:
        HomeSection.objects.get_or_create(
            type=section_type,
            defaults={"order": order, "enabled": True},
        )
    # Move shop_by_need before shop_by_skill
    HomeSection.objects.filter(type="shop_by_need").update(order=2)
    HomeSection.objects.filter(type="shop_by_skill").update(order=3)


def remove_new_sections(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    HomeSection.objects.filter(type__in=[t for t, _, _ in NEW_SECTIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0008_redesign"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homesection",
            name="type",
            field=models.CharField(
                choices=[
                    ("hero_slider", "Hero slider (banners)"),
                    ("trust_badges", "Trust badges"),
                    ("shop_by_skill", "Shop by skill"),
                    ("shop_by_need", "Shop by need"),
                    ("featured_products", "Featured products"),
                    ("shop_by_age", "Shop by age"),
                    ("sale_products", "Sale products"),
                    ("promo_banners", "Promo banners"),
                    ("new_arrivals", "New arrivals"),
                    ("shop_by_budget", "Shop by budget"),
                    ("therapist_picks", "Therapist picks"),
                    ("video", "Video section"),
                    ("gallery", "Gallery"),
                    ("testimonials", "What parents say (testimonials)"),
                    ("whatsapp_help", "WhatsApp help band"),
                    ("faq_section", "FAQ / Questions parents ask"),
                    ("save_with_bundles", "Save with bundles"),
                    ("our_story", "Our story"),
                    ("why_us", "Why parents choose LittleMove"),
                    ("final_cta", "Final CTA (Ready to find their favourite?)"),
                ],
                max_length=30,
                unique=True,
                verbose_name="Section type",
            ),
        ),
        migrations.RunPython(add_sections_and_reorder, reverse_code=remove_new_sections),
    ]
