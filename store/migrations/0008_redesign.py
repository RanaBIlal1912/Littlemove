"""Migration 0008: redesign fields + new HomeSection types."""
from django.db import migrations, models


NEW_SECTIONS = [
    ("gallery",           "Gallery / #LittleMoveKids", 11),
    ("save_with_bundles", "Save with bundles",          14),
    ("our_story",         "Our story",                  15),
]


def add_new_sections(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    for section_type, _, order in NEW_SECTIONS:
        HomeSection.objects.get_or_create(
            type=section_type,
            defaults={"order": order, "enabled": True},
        )


def remove_new_sections(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    HomeSection.objects.filter(type__in=[t for t, _, _ in NEW_SECTIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0007_bundle_ourstory"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="video",
            field=models.FileField(
                blank=True,
                help_text="Optional video background (mp4 or webm, max 15 MB). On phones the poster image is shown instead.",
                upload_to="banners/video/",
            ),
        ),
        migrations.AddField(
            model_name="storesettings",
            name="animated_bg",
            field=models.BooleanField(
                default=True,
                help_text="Slow-moving colour gradient mesh in the page background. Turn off for a plain look.",
                verbose_name="Animated background",
            ),
        ),
        migrations.AddField(
            model_name="storesettings",
            name="hero_height",
            field=models.CharField(
                choices=[("full", "Full screen (100vh)"), ("medium", "Medium (55vh)")],
                default="full",
                help_text="Height of the home page hero banner.",
                max_length=8,
                verbose_name="Hero banner height",
            ),
        ),
        migrations.AddField(
            model_name="homesection",
            name="bg_image",
            field=models.ImageField(
                blank=True,
                help_text="Optional full-width background photo for this section.",
                upload_to="sections/",
            ),
        ),
        migrations.RunPython(add_new_sections, reverse_code=remove_new_sections),
    ]
