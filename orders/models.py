import secrets

from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from store.models import Product


def make_order_number():
    # e.g. LM-2610-7K3Q : year+month and 4 unambiguous random characters
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    stamp = timezone.localtime().strftime("%y%m")
    while True:
        number = f"LM-{stamp}-" + "".join(secrets.choice(alphabet) for _ in range(4))
        if not Order.objects.filter(number=number).exists():
            return number


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "New — needs confirming"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Payment(models.TextChoices):
        COD = "cod", "Cash on delivery"
        JAZZCASH = "jazzcash", "JazzCash"
        EASYPAISA = "easypaisa", "EasyPaisa"
        BANK = "bank", "Bank transfer"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        CHECKING = "checking", "Customer says paid — check"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    number = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=60)
    address = models.TextField()
    notes = models.TextField(blank=True)

    payment_method = models.CharField(max_length=12, choices=Payment.choices, default=Payment.COD)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    transaction_id = models.CharField("Transaction ID", max_length=40, blank=True)

    subtotal = models.PositiveIntegerField()
    delivery_fee = models.PositiveIntegerField()
    total = models.PositiveIntegerField()

    courier = models.CharField(max_length=60, blank=True, help_text="e.g. TCS, Leopards, M&P")
    tracking_number = models.CharField(max_length=60, blank=True)
    internal_note = models.TextField(blank=True, help_text="Only visible in admin")

    stock_restored = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("confirm_orders", "Can confirm, hold, and cancel orders"),
            ("dispatch_orders", "Can pack, ship, deliver, and return orders"),
            ("verify_payments", "Can change payment status and transaction ID"),
            ("export_orders", "Can export orders to CSV"),
        ]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = make_order_number()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("orders:success", args=[self.number])

    @property
    def item_count(self):
        return sum(i.qty for i in self.items.all())

    @property
    def is_prepaid(self):
        return self.payment_method != self.Payment.COD

    def cancel_and_restock(self):
        """Cancel the order and put its items back in stock (only once)."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.stock_restored:
                return False
            for item in order.items.select_related("product"):
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.qty)
            order.status = Order.Status.CANCELLED
            order.stock_restored = True
            order.save(update_fields=["status", "stock_restored", "updated_at"])
        self.refresh_from_db()
        return True


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name="+")
    # Snapshot so editing/deleting a product never changes an old order.
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=40, blank=True)
    price = models.PositiveIntegerField()
    qty = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.qty} × {self.name}"

    @property
    def line_total(self):
        return self.price * self.qty
