"""
Tests for new models and features added in the professional admin dashboard upgrade:
  - HomeSection order/hide
  - Popup date rules
  - MediaItem upload validation
  - Chatbot keyword matching and rate limiting
  - Admin dashboard page loads
"""
import io
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store.models import (
    BotAnswer, BotSettings, Category, ChatLog, FAQ, HomeSection,
    MediaItem, Popup, Product, StoreSettings,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_category(name="Sensory"):
    return Category.objects.create(name=name)


def make_product(cat, name="Rings", price=1000, stock=5):
    return Product.objects.create(category=cat, name=name, price=price, stock=stock, summary="x")


# ── HomeSection tests ─────────────────────────────────────────────────────────

class HomeSectionOrderTests(TestCase):
    """HomeSection controls which sections appear on the home page and in what order."""

    def setUp(self):
        # The data migration creates sections; clear them for clean tests.
        HomeSection.objects.all().delete()

    def test_sections_render_in_order(self):
        # shop_by_need (need-grid) at order=1, shop_by_budget (price-row-tiles) at order=2
        HomeSection.objects.create(type="shop_by_need",   order=1, enabled=True)
        HomeSection.objects.create(type="shop_by_budget", order=2, enabled=True)
        cat = make_category()
        from store.models import Need
        Need.objects.create(name="Focus")
        resp = self.client.get("/")
        pos_need   = resp.content.find(b'class="need-grid"')
        pos_budget = resp.content.find(b'class="price-row-tiles"')
        self.assertNotEqual(pos_need, -1, "shop_by_need section not found")
        self.assertNotEqual(pos_budget, -1, "shop_by_budget section not found")
        self.assertLess(pos_need, pos_budget, "need should appear before budget")

    def test_disabled_section_is_hidden(self):
        HomeSection.objects.create(type="shop_by_skill", order=1, enabled=False)
        HomeSection.objects.create(type="testimonials",  order=2, enabled=True)
        cat = make_category()
        resp = self.client.get("/")
        # "cat-row" is the CSS class unique to the Shop by skill section body —
        # it does NOT appear in the navigation header.
        self.assertNotIn(b'class="cat-row"', resp.content)

    def test_enabled_section_appears(self):
        HomeSection.objects.create(type="shop_by_need", order=1, enabled=True)
        cat = make_category()
        from store.models import Need
        Need.objects.create(name="Focus and attention")
        resp = self.client.get("/")
        # "need-grid" only appears inside the shop_by_need section body
        self.assertIn(b'class="need-grid"', resp.content)

    def test_disabled_section_does_not_appear(self):
        HomeSection.objects.create(type="shop_by_need", order=1, enabled=False)
        cat = make_category()
        from store.models import Need
        Need.objects.create(name="Focus and attention")
        resp = self.client.get("/")
        # "need-grid" should be absent when the section is disabled
        self.assertNotIn(b'class="need-grid"', resp.content)

    def test_no_sections_still_renders_page(self):
        """Home page should not crash with no sections."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)


# ── Popup date rule tests ─────────────────────────────────────────────────────

class PopupGetActiveTests(TestCase):
    """Popup.get_active() should only return a valid, date-within-range, active popup."""

    def test_active_no_dates_is_shown(self):
        p = Popup.objects.create(name="Sale", title="50% Off", active=True)
        self.assertEqual(Popup.get_active(), p)

    def test_inactive_not_shown(self):
        Popup.objects.create(name="Sale", title="50% Off", active=False)
        self.assertIsNone(Popup.get_active())

    def test_future_start_not_shown_yet(self):
        future = timezone.now() + timedelta(hours=2)
        Popup.objects.create(name="Sale", title="50% Off", active=True, start_at=future)
        self.assertIsNone(Popup.get_active())

    def test_past_end_is_expired(self):
        past = timezone.now() - timedelta(hours=1)
        Popup.objects.create(name="Sale", title="50% Off", active=True, end_at=past)
        self.assertIsNone(Popup.get_active())

    def test_within_start_and_end_is_shown(self):
        now = timezone.now()
        p = Popup.objects.create(
            name="Sale", title="50% Off", active=True,
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=1),
        )
        self.assertEqual(Popup.get_active(), p)

    def test_started_no_end_is_shown(self):
        p = Popup.objects.create(
            name="Sale", title="50% Off", active=True,
            start_at=timezone.now() - timedelta(minutes=5),
        )
        self.assertEqual(Popup.get_active(), p)

    def test_no_start_with_end_in_future_is_shown(self):
        p = Popup.objects.create(
            name="Sale", title="50% Off", active=True,
            end_at=timezone.now() + timedelta(days=3),
        )
        self.assertEqual(Popup.get_active(), p)

    def test_returns_first_matching(self):
        Popup.objects.create(name="A", title="First", active=True)
        Popup.objects.create(name="B", title="Second", active=True)
        result = Popup.get_active()
        self.assertIsNotNone(result)


# ── MediaItem validation tests ────────────────────────────────────────────────

def _fake_file(name, size_bytes=100):
    """Return a SimpleUploadedFile of the given size."""
    return SimpleUploadedFile(name, b"x" * size_bytes)


class MediaItemValidationTests(TestCase):
    """MediaItem.clean() rejects wrong file types and oversized files."""

    def _media(self, type_, file=None, **kwargs):
        m = MediaItem(title="Test", type=type_, **kwargs)
        if file:
            m.file = file
        return m

    def test_valid_jpeg_passes(self):
        m = self._media(MediaItem.TYPE_IMAGE, file=_fake_file("photo.jpg"))
        m.clean()  # should not raise

    def test_valid_webp_passes(self):
        m = self._media(MediaItem.TYPE_IMAGE, file=_fake_file("photo.webp"))
        m.clean()

    def test_invalid_image_extension_rejected(self):
        from django.core.exceptions import ValidationError
        m = self._media(MediaItem.TYPE_IMAGE, file=_fake_file("photo.gif"))
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("jpg", str(ctx.exception).lower())

    def test_image_too_large_rejected(self):
        from django.core.exceptions import ValidationError
        big = _fake_file("big.jpg", size_bytes=6 * 1024 * 1024)
        m = self._media(MediaItem.TYPE_IMAGE, file=big)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("5 MB", str(ctx.exception))

    def test_valid_mp4_passes(self):
        m = self._media(MediaItem.TYPE_VIDEO, file=_fake_file("video.mp4"))
        m.clean()

    def test_invalid_video_extension_rejected(self):
        from django.core.exceptions import ValidationError
        m = self._media(MediaItem.TYPE_VIDEO, file=_fake_file("video.avi"))
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("mp4", str(ctx.exception).lower())

    def test_video_too_large_rejected(self):
        from django.core.exceptions import ValidationError
        big = _fake_file("big.mp4", size_bytes=51 * 1024 * 1024)
        m = self._media(MediaItem.TYPE_VIDEO, file=big)
        with self.assertRaises(ValidationError) as ctx:
            m.clean()
        self.assertIn("50 MB", str(ctx.exception))

    def test_no_file_no_error(self):
        m = self._media(MediaItem.TYPE_IMAGE)
        m.clean()  # no file, no error

    def test_youtube_type_no_file_no_error(self):
        m = self._media(MediaItem.TYPE_YOUTUBE, youtube_url="https://youtube.com/watch?v=abc")
        m.clean()


# ── Chatbot tests ─────────────────────────────────────────────────────────────

@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.db",
)
class ChatbotKeywordTests(TestCase):
    """Chatbot keyword matching, rate limiting, and API endpoint."""

    def setUp(self):
        BotSettings.objects.create(pk=1, enabled=True, fallback_message="I don't know.")
        cat = make_category()
        FAQ.objects.create(question="How do I pay?", answer="Cash on delivery.", order=1, active=True)
        BotAnswer.objects.create(
            question="Delivery time",
            keywords="delivery\nshipping\nhow long",
            answer="3-5 working days.",
            active=True,
        )

    def _post(self, message):
        return self.client.post(
            reverse("store:chat_api"),
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    def test_keyword_match_returns_answer(self):
        resp = self._post("how long is delivery")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("3-5", data["answer"])
        self.assertTrue(data["matched"])

    def test_faq_match_returns_answer(self):
        resp = self._post("how do I pay")
        data = resp.json()
        self.assertIn("Cash", data["answer"])
        self.assertTrue(data["matched"])

    def test_no_match_returns_fallback(self):
        resp = self._post("zebras in antarctica")
        data = resp.json()
        self.assertEqual(data["answer"], "I don't know.")
        self.assertFalse(data["matched"])

    def test_chat_is_logged(self):
        self._post("how long is delivery")
        self.assertEqual(ChatLog.objects.count(), 1)
        log = ChatLog.objects.get()
        self.assertTrue(log.matched)

    def test_empty_message_returns_400(self):
        resp = self._post("")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            reverse("store:chat_api"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_get_method_rejected(self):
        resp = self.client.get(reverse("store:chat_api"))
        self.assertEqual(resp.status_code, 405)

    def test_disabled_bot_returns_disabled_flag(self):
        BotSettings.objects.filter(pk=1).update(enabled=False)
        resp = self._post("hello")
        data = resp.json()
        self.assertTrue(data.get("disabled"))


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.db",
)
class ChatbotRateLimitTests(TestCase):
    """20 messages per hour per session; 21st should be rate-limited."""

    def setUp(self):
        BotSettings.objects.create(pk=1, enabled=True, fallback_message="dunno")

    def test_rate_limit_triggers_after_20_messages(self):
        from store.chatbot import RATE_LIMIT, RATE_WINDOW, SESSION_KEY
        # Pre-fill the session with 20 recent timestamps
        session = self.client.session
        now = timezone.now().timestamp()
        session[SESSION_KEY] = [now - 1] * RATE_LIMIT
        session.save()

        resp = self.client.post(
            reverse("store:chat_api"),
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        data = resp.json()
        self.assertTrue(data.get("rate_limited"))

    def test_under_limit_not_rate_limited(self):
        from store.chatbot import RATE_LIMIT, SESSION_KEY
        session = self.client.session
        now = timezone.now().timestamp()
        session[SESSION_KEY] = [now - 1] * (RATE_LIMIT - 1)
        session.save()

        resp = self.client.post(
            reverse("store:chat_api"),
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        data = resp.json()
        self.assertFalse(data.get("rate_limited"))

    def test_old_messages_do_not_count(self):
        """Messages older than 1 hour should not count towards the limit."""
        from store.chatbot import RATE_LIMIT, RATE_WINDOW, SESSION_KEY
        session = self.client.session
        old = timezone.now().timestamp() - RATE_WINDOW - 10  # 10 s past the window
        session[SESSION_KEY] = [old] * RATE_LIMIT  # all stale
        session.save()

        resp = self.client.post(
            reverse("store:chat_api"),
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        data = resp.json()
        self.assertFalse(data.get("rate_limited"))


# ── Admin dashboard tests ─────────────────────────────────────────────────────

class AdminDashboardTests(TestCase):
    """Admin dashboard loads and returns KPI context variables."""

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "a@x.com", "AdminPass1!")
        self.client.force_login(self.admin)

    def test_dashboard_loads(self):
        resp = self.client.get(reverse("admin:index"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_has_kpi_keys(self):
        resp = self.client.get(reverse("admin:index"))
        self.assertIn("kpi_orders_today", resp.context)
        self.assertIn("kpi_revenue_month", resp.context)
        self.assertIn("kpi_pending", resp.context)
        self.assertIn("kpi_low_stock", resp.context)

    def test_dashboard_has_chart_data(self):
        resp = self.client.get(reverse("admin:index"))
        self.assertIn("chart_labels", resp.context)
        self.assertIn("chart_orders", resp.context)
        self.assertIn("chart_revenue", resp.context)
        self.assertEqual(len(resp.context["chart_labels"]), 30)

    def test_dashboard_has_latest_orders(self):
        resp = self.client.get(reverse("admin:index"))
        self.assertIn("latest_orders", resp.context)

    def test_dashboard_has_low_stock_products(self):
        resp = self.client.get(reverse("admin:index"))
        self.assertIn("low_stock_products", resp.context)

    def test_dashboard_shows_pending_count(self):
        from orders.models import Order
        cat = make_category()
        p = make_product(cat)
        # Create a pending order directly
        from store.models import StoreSettings
        shop = StoreSettings.load()
        order = Order.objects.create(
            full_name="Test User", phone="03001234567", city="Lahore",
            address="Test address", payment_method=Order.Payment.COD,
            subtotal=1000, delivery_fee=250, total=1250,
            status=Order.Status.PENDING,
        )
        resp = self.client.get(reverse("admin:index"))
        self.assertEqual(resp.context["kpi_pending"], 1)

    def test_non_staff_redirected_from_admin(self):
        self.client.logout()
        resp = self.client.get(reverse("admin:index"))
        self.assertEqual(resp.status_code, 302)

    def test_admin_store_pages_load(self):
        """Key admin changelist pages should return 200."""
        urls = [
            reverse("admin:store_product_changelist"),
            reverse("admin:store_storesettings_changelist"),
            reverse("admin:store_homesection_changelist"),
            reverse("admin:store_banner_changelist"),
            reverse("admin:store_popup_changelist"),
            reverse("admin:store_mediaitem_changelist"),
            reverse("admin:store_faq_changelist"),
            reverse("admin:store_botanswer_changelist"),
            reverse("admin:store_chatlog_changelist"),
            reverse("admin:orders_order_changelist"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
