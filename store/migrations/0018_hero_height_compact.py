"""
Change StoreSettings.hero_height default to "compact" and add the new
"compact" choice alongside the existing "medium" and "full" choices.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0017_drop_ur_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storesettings",
            name="hero_height",
            field=models.CharField(
                choices=[
                    ("compact", "Compact (recommended — ~380px)"),
                    ("medium", "Medium (~480px)"),
                    ("full", "Full screen (~520px)"),
                ],
                default="compact",
                help_text="Height of the home page hero banner.",
                max_length=8,
                verbose_name="Hero banner height",
            ),
        ),
    ]
