"""
Migration 0007: Bundle model, OurStory singleton model, new HomeSection types,
announcement default change, default OurStory row.
"""
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


OLD_ANNOUNCEMENT = (
    "Free delivery on orders over Rs 5,000 | Cash on delivery all over Pakistan | "
    "Toys chosen with therapists"
)
NEW_ANNOUNCEMENT = "Free delivery on orders of Rs 5,000 or more"


def add_new_sections(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    HomeSection.objects.get_or_create(
        type="save_with_bundles",
        defaults={"order": 14, "enabled": True},
    )
    HomeSection.objects.get_or_create(
        type="our_story",
        defaults={"order": 15, "enabled": True},
    )


def remove_new_sections(apps, schema_editor):
    HomeSection = apps.get_model("store", "HomeSection")
    HomeSection.objects.filter(type__in=["save_with_bundles", "our_story"]).delete()


def create_our_story(apps, schema_editor):
    OurStory = apps.get_model("store", "OurStory")
    OurStory.objects.get_or_create(pk=1)


def remove_our_story(apps, schema_editor):
    pass  # leave it; reverse is a no-op


def update_announcement(apps, schema_editor):
    StoreSettings = apps.get_model("store", "StoreSettings")
    StoreSettings.objects.filter(announcement=OLD_ANNOUNCEMENT).update(
        announcement=NEW_ANNOUNCEMENT
    )


def revert_announcement(apps, schema_editor):
    pass  # no need to revert


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_chatbot_starter_data"),
    ]

    operations = [
        # --- Bundle model ---
        migrations.CreateModel(
            name="Bundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("bundle_price", models.PositiveIntegerField(
                    help_text="Total price for the whole bundle (Rs). Should be lower than the sum of individual prices.",
                    validators=[django.core.validators.MinValueValidator(1)],
                )),
                ("image", models.ImageField(
                    blank=True,
                    help_text="Optional banner image for the bundle (1200×500 recommended).",
                    upload_to="bundles/",
                )),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Bundle", "verbose_name_plural": "Bundles"},
        ),
        migrations.AddField(
            model_name="bundle",
            name="products",
            field=models.ManyToManyField(
                help_text="Choose 2 or more products to include in this bundle.",
                related_name="bundles",
                to="store.product",
            ),
        ),

        # --- OurStory singleton ---
        migrations.CreateModel(
            name="OurStory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Our story", max_length=120)),
                ("body", models.TextField(
                    default=(
                        "LittleMove was born at Wellness Rehabilitation Clinic in Bahawalpur. "
                        "Our therapists work with children every day and kept meeting the same challenge: "
                        "parents wanted to continue the therapy exercises at home, but couldn't find the "
                        "right toys in Pakistan.\n\n"
                        "So we started selecting the toys we use in our own sessions — sensory, motor and "
                        "speech toys that are safe, age-right and actually work. Every toy we sell is one "
                        "our therapists have used themselves."
                    ),
                )),
                ("photo", models.ImageField(
                    blank=True,
                    help_text="A photo of the clinic, team or children playing.",
                    upload_to="our_story/",
                )),
                ("active", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Our story section", "verbose_name_plural": "Our story section"},
        ),

        # --- Announcement default change ---
        migrations.AlterField(
            model_name="storesettings",
            name="announcement",
            field=models.CharField(
                blank=True,
                default="Free delivery on orders of Rs 5,000 or more",
                help_text="Top bar messages. Separate several with | and they rotate.",
                max_length=300,
            ),
        ),

        # --- Data operations ---
        migrations.RunPython(update_announcement, revert_announcement),
        migrations.RunPython(add_new_sections, remove_new_sections),
        migrations.RunPython(create_our_story, remove_our_story),
    ]
