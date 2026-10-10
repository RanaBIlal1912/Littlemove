import secrets

from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from store.models import Product


def make_order_number():
    # e.g. LM-2610-7K3Q : year+month and 4 unambiguous random characters
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    stamp = timezone.localtime().strftime("%y%m")
    while True:
        number = f"LM-{stamp}-" + "".join(secrets.choice(alphabet) for _ in range(4))
        if not Order.objects.filter(number=number).exists():
            return number


STATUS_COLORS = {
    "pending":   "#b54708",
    "confirmed": "#1d4ed8",
    "packed":    "#5b21b6",
    "shipped":   "#0e7490",
    "delivered": "#067647",
    "cancelled": "#b42318",
    "on_hold":   "#6b7280",
    "returned":  "#c2410c",
}

PAYMENT_COLORS = {
    "unpaid":   "#b42318",
    "checking": "#b54708",
    "paid":     "#067647",
    "refunded": "#6b7280",
}

VALID_TRANSITIONS = {
    "pending":   {"confirmed", "on_hold", "cancelled"},
    "confirmed": {"packed", "on_hold", "cancelled"},
    "packed":    {"shipped", "cancelled"},
    "shipped":   {"delivered", "returned"},
    "delivered": {"returned"},
    "on_hold":   {"confirmed", "cancelled"},
    "cancelled": set(),
    "returned":  set(),
}


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   _("New – needs confirming")
        CONFIRMED = "confirmed", _("Confirmed")
        PACKED    = "packed",    _("Packed – ready for pickup")
        SHIPPED   = "shipped",   _("Picked up – on the way")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        ON_HOLD   = "on_hold",   _("On hold")
        RETURNED  = "returned",  _("Returned")

    class Payment(models.TextChoices):
        COD = "cod", _("Cash on delivery")
        JAZZCASH = "jazzcash", "JazzCash"
        EASYPAISA = "easypaisa", "EasyPaisa"
        BANK = "bank", _("Bank transfer")

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", _("Unpaid")
        CHECKING = "checking", _("Customer says paid - check")
        PAID = "paid", _("Paid")
        REFUNDED = "refunded", _("Refunded")

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

    def _restore_stock(self):
        for item in self.items.select_related("product"):
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.qty)
        self.stock_restored = True

    def cancel_and_restock(self):
        """Cancel the order and put its items back in stock (only once)."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.stock_restored:
                return False
            order._restore_stock()
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "stock_restored", "updated_at"])
        self.refresh_from_db()
        return True

    def return_and_restock(self):
        """Return the order and put its items back in stock (only once)."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.stock_restored:
                return False
            order._restore_stock()
            order.status = Order.Status.RETURNED
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


class OrderEvent(models.Model):
    class Kind(models.TextChoices):
        STATUS  = "status",  "Status change"
        PAYMENT = "payment", "Payment change"
        NOTE    = "note",    "Note added"

    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    user       = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    kind       = models.CharField(max_length=10, choices=Kind.choices)
    from_value = models.CharField(max_length=40, blank=True)
    to_value   = models.CharField(max_length=40, blank=True)
    note       = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.number} {self.kind}"

    def describe(self):
        if self.kind == self.Kind.STATUS:
            try:
                fl = Order.Status(self.from_value).label
            except Exception:
                fl = self.from_value or "—"
            try:
                tl = Order.Status(self.to_value).label
            except Exception:
                tl = self.to_value or "—"
            return f"{fl} → {tl}"
        if self.kind == self.Kind.PAYMENT:
            try:
                fl = Order.PaymentStatus(self.from_value).label
            except Exception:
                fl = self.from_value or "—"
            try:
                tl = Order.PaymentStatus(self.to_value).label
            except Exception:
                tl = self.to_value or "—"
            return f"Payment: {fl} → {tl}"
        if self.kind == self.Kind.NOTE:
            return f"Note: {self.note[:80]}"
        return self.kind
