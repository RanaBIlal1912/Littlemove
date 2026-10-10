from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="order",
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("confirm_orders", "Can confirm, hold, and cancel orders"),
                    ("dispatch_orders", "Can pack, ship, deliver, and return orders"),
                    ("verify_payments", "Can change payment status and transaction ID"),
                    ("export_orders", "Can export orders to CSV"),
                ],
            },
        ),
    ]
