from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0011_phone_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="botanswer",
            name="show_as_quick",
            field=models.BooleanField(
                default=False,
                verbose_name="Show as quick button",
                help_text="Show this Q&A as a quick-reply chip in the chat widget (max 6 total).",
            ),
        ),
        migrations.AddField(
            model_name="botanswer",
            name="quick_label",
            field=models.CharField(
                blank=True,
                max_length=40,
                verbose_name="Button text",
                help_text="Label on the chip. Falls back to the question if blank.",
            ),
        ),
        migrations.AddField(
            model_name="botanswer",
            name="quick_order",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Button order",
            ),
        ),
        migrations.AddField(
            model_name="botanswer",
            name="action",
            field=models.CharField(
                choices=[
                    ("normal", "Normal answer"),
                    ("toy_finder", "Start toy finder"),
                    ("whatsapp", "Open WhatsApp"),
                ],
                default="normal",
                max_length=20,
            ),
        ),
    ]
