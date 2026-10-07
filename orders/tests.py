from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import Category, Product, StoreSettings

from .models import Order


@override_settings(ORDER_ALERT_EMAIL="")
class CheckoutTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Fine motor")
        self.rings = Product.objects.create(category=cat, name="Rings", price=1000, stock=5, summary="x")
        self.cards = Product.objects.create(category=cat, name="Cards", price=500, stock=2, summary="x")
        shop = StoreSettings.load()
        shop.delivery_fee, shop.free_delivery_over = 250, 5000
        shop.save()

    def add(self, product, qty=1):
        return self.client.post(reverse("store:cart_add", args=[product.pk]), {"qty": qty})

    def checkout(self, **overrides):
        data = {"full_name": "Ayesha Khan", "phone": "0300-1234567", "city": "Bahawalpur",
                "address": "House 12, Street 4, Model Town", "payment_method": "cod"}
        data.update(overrides)
        return self.client.post(reverse("orders:checkout"), data)

    def test_full_order_reduces_stock_and_snapshots_prices(self):
        self.add(self.rings, 2)
        self.add(self.cards, 1)
        resp = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(resp, order.get_absolute_url())
        self.assertEqual((order.subtotal, order.delivery_fee, order.total), (2500, 250, 2750))
        self.assertEqual(order.phone, "03001234567")
        self.rings.refresh_from_db(); self.cards.refresh_from_db()
        self.assertEqual((self.rings.stock, self.cards.stock), (3, 1))
        # price change later must not touch the order
        Product.objects.filter(pk=self.rings.pk).update(price=9999)
        self.assertEqual(order.items.get(name="Rings").price, 1000)
        # cart emptied, success page visible to this browser only
        self.assertEqual(self.client.session.get("cart"), {})
        self.assertContains(self.client.get(order.get_absolute_url()), order.number)

    def test_free_delivery_threshold(self):
        self.add(self.rings, 5)
        self.checkout()
        self.assertEqual(Order.objects.get().delivery_fee, 0)

    def test_cart_cannot_exceed_stock(self):
        self.add(self.cards, 10)
        self.assertEqual(self.client.session["cart"][str(self.cards.pk)], 2)

    def test_stock_sold_elsewhere_blocks_order(self):
        self.add(self.cards, 2)
        Product.objects.filter(pk=self.cards.pk).update(stock=1)  # someone else bought one
        resp = self.checkout()
        self.assertRedirects(resp, reverse("store:cart"))
        self.assertFalse(Order.objects.exists())
        self.cards.refresh_from_db()
        self.assertEqual(self.cards.stock, 1)

    def test_prepaid_requires_transaction_id(self):
        self.add(self.rings)
        resp = self.checkout(payment_method="jazzcash")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.checkout(payment_method="jazzcash", transaction_id="TX123")
        self.assertEqual(Order.objects.get().payment_status, Order.PaymentStatus.CHECKING)

    def test_bad_phone_rejected(self):
        self.add(self.rings)
        resp = self.checkout(phone="12345")
        self.assertContains(resp, "Pakistani mobile number")
        self.assertFalse(Order.objects.exists())

    def test_honeypot_blocks_bots(self):
        self.add(self.rings)
        self.checkout(website="http://spam")
        self.assertFalse(Order.objects.exists())

    def test_hidden_product_cannot_be_bought(self):
        self.add(self.rings)
        Product.objects.filter(pk=self.rings.pk).update(is_active=False)
        resp = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(resp, reverse("store:shop"))

    def test_other_browser_cannot_open_order_page(self):
        self.add(self.rings)
        self.checkout()
        url = Order.objects.get().get_absolute_url()
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_track_needs_matching_phone(self):
        self.add(self.rings)
        self.checkout()
        order = Order.objects.get()
        ok = self.client.get(reverse("orders:track"), {"number": order.number.lower(), "phone": "+92 300 1234567"})
        self.assertContains(ok, f"Order {order.number}")
        bad = self.client.get(reverse("orders:track"), {"number": order.number, "phone": "03119999999"})
        self.assertContains(bad, "No order matches")

    def test_cancel_restocks_once(self):
        self.add(self.rings, 2)
        self.checkout()
        order = Order.objects.get()
        self.assertTrue(order.cancel_and_restock())
        self.assertFalse(order.cancel_and_restock())
        self.rings.refresh_from_db()
        self.assertEqual(self.rings.stock, 5)
        self.assertEqual(order.status, Order.Status.CANCELLED)


class PagesTests(TestCase):
    def test_public_pages_render(self):
        cat = Category.objects.create(name="Sensory play", color="sky")
        p = Product.objects.create(category=cat, name="Balls <b>", price=900, stock=1, summary="soft")
        for url in ["/", "/shop/", f"/shop/?category={cat.slug}&age=2-4&sort=price-low&q=ball",
                    p.get_absolute_url(), "/cart/", "/track/", "/delivery-and-returns/",
                    "/sitemap.xml", "/robots.txt"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        # names are escaped everywhere
        self.assertNotContains(self.client.get(p.get_absolute_url()), "Balls <b>")

    def test_shop_by_need(self):
        from store.models import Need
        cat = Category.objects.create(name="Sensory play")
        calm = Need.objects.create(name="Calm and focus")
        squeeze = Product.objects.create(category=cat, name="Squeeze kit", price=900, stock=2, summary="x")
        Product.objects.create(category=cat, name="Loud drum", price=900, stock=2, summary="x")
        squeeze.needs.add(calm)
        resp = self.client.get(calm.get_absolute_url())
        self.assertContains(resp, "Squeeze kit")
        self.assertNotContains(resp, "Loud drum")
        self.assertContains(self.client.get(squeeze.get_absolute_url()), "Parents often choose this for")
        self.assertRedirects(self.client.get("/shop/?need=nope"), "/shop/")

    def test_unknown_category_falls_back_to_shop(self):
        self.assertRedirects(self.client.get("/shop/?category=nope"), "/shop/")

    def test_filters_sale_pick_and_price(self):
        cat = Category.objects.create(name="Gross motor")
        Product.objects.create(category=cat, name="Board", price=4000, compare_at_price=5000,
                               stock=3, summary="x", therapist_pick=True)
        Product.objects.create(category=cat, name="Ball", price=500, stock=3, summary="x")
        self.assertContains(self.client.get("/shop/?sale=1"), "1 toy")
        self.assertContains(self.client.get("/shop/?pick=1"), "Board")
        resp = self.client.get("/shop/?max=1000")
        self.assertContains(resp, "Ball")
        self.assertNotContains(resp, "Board</a>")
        self.assertContains(self.client.get("/"), "-20%")
