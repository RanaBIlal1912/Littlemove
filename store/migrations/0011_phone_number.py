from django.db import migrations, models

# Old → new phone number variants (WhatsApp number only; JazzCash/EasyPaisa untouched)
OLD_TO_NEW = [
    ("+92 317 3661912", "+92 310 6521912"),
    ("923173661912",    "923106521912"),
    ("03173661912",     "03106521912"),
]


def update_phone_numbers(apps, schema_editor):
    """Replace old number in BotAnswer.answer and FAQ.answer text fields."""
    for model_name in ("BotAnswer", "FAQ"):
        Model = apps.get_model("store", model_name)
        for obj in Model.objects.all():
            updated = obj.answer
            for old, new in OLD_TO_NEW:
                updated = updated.replace(old, new)
            if updated != obj.answer:
                obj.answer = updated
                obj.save(update_fields=["answer"])

    # Update StoreSettings.whatsapp_number if it still holds the old value.
    # JazzCash/EasyPaisa fields are deliberately left unchanged.
    StoreSettings = apps.get_model("store", "StoreSettings")
    StoreSettings.objects.filter(whatsapp_number="923173661912").update(
        whatsapp_number="923106521912"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0010_alter_homesection_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storesettings",
            name="whatsapp_number",
            field=models.CharField(
                default="923106521912",
                help_text="International format without + or spaces, e.g. 923106521912",
                max_length=20,
            ),
        ),
        migrations.RunPython(update_phone_numbers, migrations.RunPython.noop),
    ]
