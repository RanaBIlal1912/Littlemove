"""Order placement: the one place that turns a cart into an order."""
import logging
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F

from store.models import Product, StoreSettings

from .models import Order, OrderItem

log = logging.getLogger(__name__)


class OutOfStock(Exception):
    def __init__(self, problems):
        self.problems = problems  # list of (product_name, available)
        super().__init__("Some items are out of stock")


def place_order(form, cart):
    """Create the order, snapshot prices and reduce stock atomically.

    Raises OutOfStock if any line can no longer be fulfilled; nothing is saved then.
    """
    lines = cart.lines()
    if not lines:
        raise OutOfStock([])

    shop = StoreSettings.load()
    with transaction.atomic():
        ids = [line.product.pk for line in lines]
        locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids)}

        problems = []
        for line in lines:
            product = locked.get(line.product.pk)
            if product is None or not product.is_active or product.stock < line.qty:
                problems.append((line.product.name, product.stock if product else 0))
        if problems:
            raise OutOfStock(problems)

        subtotal = sum(locked[line.product.pk].price * line.qty for line in lines)
        delivery = shop.delivery_for(subtotal)

        order = form.save(commit=False)
        order.subtotal = subtotal
        order.delivery_fee = delivery
        order.total = subtotal + delivery
        if order.payment_method != Order.Payment.COD:
            order.payment_status = Order.PaymentStatus.CHECKING
        else:
            order.transaction_id = ""
        order.save()

        for line in lines:
            product = locked[line.product.pk]
            OrderItem.objects.create(
                order=order, product=product, name=product.name, sku=product.sku,
                price=product.price, qty=line.qty,
            )
            Product.objects.filter(pk=product.pk).update(stock=F("stock") - line.qty)

    cart.clear()
    transaction.on_commit(lambda: notify_store(order))
    return order


def notify_store(order):
    if not settings.ORDER_ALERT_EMAIL:
        return
    items = "\n".join(f"- {i.qty} x {i.name} @ Rs {i.price}" for i in order.items.all())
    body = (
        f"New order {order.number}\n\n{order.full_name} — {order.phone}\n{order.address}, {order.city}\n\n"
        f"{items}\n\nTotal: Rs {order.total} ({order.get_payment_method_display()})"
    )
    try:
        send_mail(f"New order {order.number} — Rs {order.total}", body,
                  settings.DEFAULT_FROM_EMAIL, [settings.ORDER_ALERT_EMAIL])
    except Exception:  # an email hiccup must never lose an order
        log.exception("Order alert email failed for %s", order.number)


def whatsapp_link(order):
    """wa.me link the customer can tap to send their order to the store."""
    shop = StoreSettings.load()
    items = "\n".join(f"• {i.qty} × {i.name}" for i in order.items.all())
    text = (
        f"Assalam o Alaikum! I just placed order {order.number}.\n{items}\n"
        f"Total: Rs {order.total:,} ({order.get_payment_method_display()})"
    )
    if order.transaction_id:
        text += f"\nTransaction ID: {order.transaction_id}"
    return f"https://wa.me/{shop.whatsapp_number}?text={quote(text)}"
