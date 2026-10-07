"""Session cart. Stores only {product_id: qty}; prices are always read fresh
from the database so a stale session can never set the price."""
from dataclasses import dataclass

from django.conf import settings

from .models import Product, StoreSettings

MAX_QTY_PER_ITEM = 20


@dataclass
class CartLine:
    product: Product
    qty: int

    @property
    def line_total(self):
        return self.product.price * self.qty

    @property
    def over_stock(self):
        return self.qty > self.product.stock


class Cart:
    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(settings.CART_SESSION_KEY) or {}
        # Keep only well-formed entries.
        self.data = {}
        for k, v in raw.items():
            try:
                pid, qty = int(k), int(v)
            except (TypeError, ValueError):
                continue
            if qty > 0:
                self.data[str(pid)] = min(qty, MAX_QTY_PER_ITEM)

    def _save(self):
        self.session[settings.CART_SESSION_KEY] = self.data
        self.session.modified = True

    def add(self, product, qty=1):
        current = self.data.get(str(product.pk), 0)
        self.set(product, current + qty)

    def set(self, product, qty):
        qty = max(0, min(int(qty), MAX_QTY_PER_ITEM, product.stock))
        if qty == 0:
            self.data.pop(str(product.pk), None)
        else:
            self.data[str(product.pk)] = qty
        self._save()

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    def lines(self):
        ids = [int(k) for k in self.data]
        products = {p.pk: p for p in Product.objects.live().filter(pk__in=ids).select_related("category")}
        result = []
        for k, qty in self.data.items():
            product = products.get(int(k))
            if product:
                result.append(CartLine(product, qty))
        return result

    @property
    def count(self):
        return sum(self.data.values())

    def summary(self):
        lines = self.lines()
        subtotal = sum(line.line_total for line in lines)
        shop = StoreSettings.load()
        delivery = shop.delivery_for(subtotal)
        to_free = 0
        if shop.free_delivery_over and 0 < subtotal < shop.free_delivery_over:
            to_free = shop.free_delivery_over - subtotal
        return {
            "lines": lines,
            "subtotal": subtotal,
            "delivery": delivery,
            "total": subtotal + delivery,
            "to_free_delivery": to_free,
            "has_problems": any(line.over_stock for line in lines),
        }
