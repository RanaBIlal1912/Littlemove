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
    BotAnswer, BotSettings, Bundle, Category, ChatLog, FAQ, HomeSection,
    MediaItem, OurStory, Popup, Product, StoreSettings,
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


# ── Upload validation tests ───────────────────────────────────────────────────

class UploadValidationTests(TestCase):
    """store/uploads.py: validate_upload, detect_kind, validate_zip_safety."""

    def _file(self, name, content=b"x" * 100):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content)

    def _jpeg(self, name="photo.jpg"):
        # minimal JPEG magic bytes
        content = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        return self._file(name, content)

    def _mp4(self, name="video.mp4"):
        # ftyp MP4 magic
        content = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 100
        return self._file(name, content)

    def _pdf(self, name="doc.pdf"):
        return self._file(name, b'%PDF-1.4 ' + b'\x00' * 100)

    def _exe(self, name="prog.exe"):
        return self._file(name, b'\x4d\x5a' + b'\x00' * 100)  # MZ header

    def test_jpeg_image_accepted(self):
        from store.uploads import validate_upload
        kind = validate_upload(self._jpeg(), allow_kinds=("image",))
        self.assertEqual(kind, "image")

    def test_mp4_accepted_as_video(self):
        from store.uploads import validate_upload
        kind = validate_upload(self._mp4(), allow_kinds=("video",))
        self.assertEqual(kind, "video")

    def test_mp4_rejected_as_image_only(self):
        from django.core.exceptions import ValidationError
        from store.uploads import validate_upload
        with self.assertRaises(ValidationError):
            validate_upload(self._mp4(), allow_kinds=("image",))

    def test_exe_always_blocked(self):
        from django.core.exceptions import ValidationError
        from store.uploads import validate_upload
        with self.assertRaises(ValidationError):
            validate_upload(self._exe(), allow_kinds=("image",))

    def test_exe_renamed_to_jpg_rejected(self):
        """Magic bytes win over extension."""
        from django.core.exceptions import ValidationError
        from store.uploads import validate_upload
        # MZ header in a .jpg file
        f = self._file("photo.jpg", b'\x4d\x5a' + b'\x00' * 100)
        with self.assertRaises(ValidationError):
            validate_upload(f, allow_kinds=("image",))

    def test_svg_blocked_by_extension(self):
        from django.core.exceptions import ValidationError
        from store.uploads import validate_upload
        f = self._file("icon.svg", b'<svg xmlns="http://www.w3.org/2000/svg">')
        with self.assertRaises(ValidationError):
            validate_upload(f, allow_kinds=("image",))

    def test_pdf_accepted_as_document(self):
        from store.uploads import validate_upload
        kind = validate_upload(self._pdf(), allow_kinds=("document",))
        self.assertEqual(kind, "document")

    def test_oversize_rejected(self):
        from django.core.exceptions import ValidationError
        from store.uploads import validate_upload
        big = self._file("big.jpg", b'\xff\xd8\xff\xe0' + b'\x00' * (11 * 1024 * 1024))
        with self.assertRaises(ValidationError) as ctx:
            validate_upload(big, allow_kinds=("image",))
        self.assertIn("MB", str(ctx.exception))

    def test_zip_traversal_rejected(self):
        from django.core.exceptions import ValidationError
        from store.uploads import validate_zip_safety
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../../etc/passwd", "root:x:0:0")
        buf.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("archive.zip", buf.read())
        with self.assertRaises(ValidationError):
            validate_zip_safety(f)

    def test_zip_safe_returns_member_names(self):
        from store.uploads import validate_zip_safety
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("photo.jpg", b'\xff\xd8\xff\xe0' + b'\x00' * 20)
        buf.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("archive.zip", buf.read())
        names = validate_zip_safety(f)
        self.assertIn("photo.jpg", names)


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
            # store_storesettings_changelist now redirects to the edit form — tested separately
            reverse("admin:store_homesection_changelist"),
            reverse("admin:store_banner_changelist"),
            reverse("admin:store_popup_changelist"),
            reverse("admin:store_mediaitem_changelist"),
            reverse("admin:store_faq_changelist"),
            reverse("admin:store_botanswer_changelist"),
            reverse("admin:store_chatlog_changelist"),
            reverse("admin:orders_order_changelist"),
            reverse("admin:store_bundle_changelist"),
            reverse("admin:store_ourstory_changelist"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


# ── Bundle tests ──────────────────────────────────────────────────────────────

class BundleTests(TestCase):
    """Bundle model, detail page, and add-to-cart endpoint."""

    def setUp(self):
        self.cat = make_category("Motor")
        self.p1 = make_product(self.cat, "Rings", 1000, stock=5)
        self.p2 = make_product(self.cat, "Beads", 1500, stock=5)
        self.bundle = Bundle.objects.create(
            name="Starter Bundle",
            bundle_price=2000,
            active=True,
        )
        self.bundle.products.set([self.p1, self.p2])

    def test_bundle_model_str(self):
        self.assertEqual(str(self.bundle), "Starter Bundle")

    def test_bundle_slug_auto_generated(self):
        self.assertEqual(self.bundle.slug, "starter-bundle")

    def test_bundle_regular_price(self):
        self.assertEqual(self.bundle.regular_price, 2500)

    def test_bundle_savings(self):
        self.assertEqual(self.bundle.savings, 500)

    def test_bundle_detail_page_loads(self):
        resp = self.client.get(reverse("store:bundle_detail", args=[self.bundle.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Starter Bundle")

    def test_bundle_detail_404_for_inactive(self):
        self.bundle.active = False
        self.bundle.save()
        resp = self.client.get(reverse("store:bundle_detail", args=[self.bundle.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_bundle_add_to_cart_adds_all_products(self):
        resp = self.client.post(
            reverse("store:bundle_add_to_cart", args=[self.bundle.pk]),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        cart_pids = [item["pid"] for item in data["items"]]
        self.assertIn(self.p1.pk, cart_pids)
        self.assertIn(self.p2.pk, cart_pids)

    def test_bundle_add_to_cart_cart_count(self):
        resp = self.client.post(
            reverse("store:bundle_add_to_cart", args=[self.bundle.pk]),
            HTTP_ACCEPT="application/json",
        )
        data = resp.json()
        self.assertEqual(data["cart_count"], 2)


# ── OurStory tests ────────────────────────────────────────────────────────────

class OurStoryTests(TestCase):
    """OurStory singleton appears on the home page when the section is enabled."""

    def setUp(self):
        HomeSection.objects.all().delete()

    def test_our_story_section_shows_body_text(self):
        HomeSection.objects.create(type="our_story", order=15, enabled=True)
        OurStory.objects.update_or_create(pk=1, defaults={"title": "Our story", "body": "We started in Bahawalpur.", "active": True})
        resp = self.client.get("/")
        self.assertContains(resp, "We started in Bahawalpur.")

    def test_our_story_hidden_when_inactive(self):
        HomeSection.objects.create(type="our_story", order=15, enabled=True)
        OurStory.objects.update_or_create(pk=1, defaults={"title": "Our story", "body": "We started in Bahawalpur.", "active": False})
        resp = self.client.get("/")
        self.assertNotContains(resp, "We started in Bahawalpur.")

    def test_our_story_load_creates_singleton(self):
        OurStory.objects.all().delete()
        obj = OurStory.load()
        self.assertEqual(obj.pk, 1)
        self.assertEqual(OurStory.objects.count(), 1)


# ── Bulk photo upload tests ───────────────────────────────────────────────────

import zipfile as _zipfile


def _make_png_bytes():
    """Return bytes of a valid 1×1 white PNG via Pillow."""
    from PIL import Image as PilImage
    buf = io.BytesIO()
    PilImage.new("RGB", (1, 1), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_zip(folders):
    """
    Build an in-memory ZIP where `folders` is:
        { "FolderName": {"img.png": <bytes>, ...}, ... }
    """
    buf = io.BytesIO()
    with _zipfile.ZipFile(buf, "w") as zf:
        for folder, files in folders.items():
            for filename, data in files.items():
                zf.writestr(f"{folder}/{filename}", data)
    buf.seek(0)
    return buf.read()


class BulkUploadMatchTests(TestCase):
    """Unit tests for process_bulk_zip matching and reporting logic."""

    def setUp(self):
        cat = make_category()
        self.p1 = Product.objects.create(
            category=cat, name="Stacking Rings", sku="RING01",
            slug="stacking-rings", price=1000, stock=5, summary="x",
        )
        self.p2 = Product.objects.create(
            category=cat, name="Puzzle Board", sku="PUZ02",
            slug="puzzle-board", price=1500, stock=3, summary="x",
        )
        self.png = _make_png_bytes()

    def test_match_by_name_exact(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"Stacking Rings": {"a.png": self.png}})
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0][0].pk, self.p1.pk)
        self.assertEqual(result["unmatched"], [])

    def test_match_by_name_case_insensitive(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"stacking  rings": {"b.png": self.png}})
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0][0].pk, self.p1.pk)

    def test_match_by_sku(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"RING01": {"c.png": self.png}})
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0][0].pk, self.p1.pk)

    def test_match_by_slug(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"puzzle-board": {"d.png": self.png}})
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0][0].pk, self.p2.pk)

    def test_unmatched_folder_reported(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({
            "Stacking Rings": {"a.png": self.png},
            "No Such Product": {"x.png": self.png},
        })
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertIn("No Such Product", result["unmatched"])

    def test_non_image_file_rejected(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"Stacking Rings": {"readme.txt": b"not an image"}})
        result = process_bulk_zip(data)
        self.assertEqual(result["matched"], [])
        self.assertIn("Stacking Rings", result["unmatched"])

    def test_corrupt_image_rejected(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({"Stacking Rings": {"bad.png": b"\x89PNG corrupted"}})
        result = process_bulk_zip(data)
        self.assertEqual(result["matched"], [])

    def test_macosx_folders_ignored(self):
        from store.bulk_upload import process_bulk_zip
        data = _make_zip({
            "__MACOSX": {"._a.png": self.png},
            "Stacking Rings": {"a.png": self.png},
        })
        result = process_bulk_zip(data)
        self.assertEqual(len(result["matched"]), 1)
        self.assertNotIn("__MACOSX", result["unmatched"])

    def test_bad_zip_returns_error(self):
        from store.bulk_upload import process_bulk_zip
        result = process_bulk_zip(b"not a zip file")
        self.assertTrue(len(result["errors"]) > 0)

    @override_settings(DEBUG=False)
    def test_multiple_images_creates_photo_rows(self):
        from store.bulk_upload import process_bulk_zip
        from store.models import ProductPhoto
        png2 = _make_png_bytes()
        data = _make_zip({"Stacking Rings": {"a.png": self.png, "b.png": png2}})
        result = process_bulk_zip(data)
        self.assertEqual(result["matched"][0][1], 2)
        self.assertEqual(ProductPhoto.objects.filter(product=self.p1).count(), 1)
        self.p1.refresh_from_db()
        self.assertTrue(bool(self.p1.image))


class BulkUploadViewTests(TestCase):
    """Integration tests for the admin bulk upload view."""

    def setUp(self):
        self.staff = User.objects.create_user("staff2", password="pw", is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)
        cat = make_category("Cat2")
        self.product = Product.objects.create(
            category=cat, name="Test Toy", sku="TOY01",
            slug="test-toy", price=999, stock=10, summary="y",
        )

    def test_get_page_loads(self):
        url = reverse("admin:store_product_bulk_upload")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk photo upload")

    def test_anonymous_redirected(self):
        self.client.logout()
        url = reverse("admin:store_product_bulk_upload")
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    def test_post_no_file_shows_error(self):
        url = reverse("admin:store_product_bulk_upload")
        resp = self.client.post(url, {})
        self.assertContains(resp, "Please choose")

    def test_post_valid_zip_shows_report(self):
        png = _make_png_bytes()
        data = _make_zip({"Test Toy": {"photo.png": png}})
        url = reverse("admin:store_product_bulk_upload")
        resp = self.client.post(url, {"zipfile": SimpleUploadedFile("up.zip", data, content_type="application/zip")})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Toy")


# ── StoreSettings admin redirect tests ───────────────────────────────────────

class StoreSettingsAdminTests(TestCase):
    """StoreSettings changelist redirects to the singleton edit form directly."""

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_ss", "ss@x.com", "AdminPass1!")
        self.client.force_login(self.admin)
        StoreSettings.objects.all().delete()

    def test_changelist_redirects_to_add_when_no_settings(self):
        resp = self.client.get(reverse("admin:store_storesettings_changelist"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("add", resp["Location"])

    def test_changelist_redirects_to_change_when_settings_exist(self):
        settings = StoreSettings.objects.create()
        resp = self.client.get(reverse("admin:store_storesettings_changelist"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/{settings.pk}/change/", resp["Location"])

    def test_change_page_loads(self):
        settings = StoreSettings.objects.create()
        resp = self.client.get(reverse("admin:store_storesettings_change", args=[settings.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_non_staff_cannot_access_settings(self):
        self.client.logout()
        resp = self.client.get(reverse("admin:store_storesettings_changelist"))
        self.assertNotEqual(resp.status_code, 200)


# ── Multi-photo upload admin tests ────────────────────────────────────────────

class MultiPhotoUploadTests(TestCase):
    """Uploading multiple extra photos via the product admin creates ProductPhoto rows."""

    def setUp(self):
        self.staff = User.objects.create_superuser("admin_ph", "ph@x.com", "AdminPass1!")
        self.client.force_login(self.staff)
        self.cat = Category.objects.create(name="Motor2")
        self.product = Product.objects.create(
            category=self.cat, name="Photo Toy", price=1000, stock=5, summary="z",
        )

    def test_extra_photos_creates_product_photo_rows(self):
        from store.admin import ProductAdmin
        from store.models import ProductPhoto
        from django.contrib.admin import site as admin_site
        from django.test import RequestFactory
        from django.utils.datastructures import MultiValueDict
        from unittest.mock import MagicMock

        png = _make_png_bytes()
        f1 = SimpleUploadedFile("extra1.png", png, content_type="image/png")
        f2 = SimpleUploadedFile("extra2.png", png, content_type="image/png")

        # Build a minimal mock request with FILES containing two photos
        request = MagicMock()
        request.FILES = MultiValueDict({"extra_photos": [f1, f2]})

        form = MagicMock()
        form.instance = self.product

        admin_instance = ProductAdmin(Product, admin_site)
        admin_instance.save_related(request, form, [], True)

        count = ProductPhoto.objects.filter(product=self.product).count()
        self.assertEqual(count, 2)

    def test_no_extra_photos_creates_no_rows(self):
        from store.admin import ProductAdmin
        from store.models import ProductPhoto
        from django.contrib.admin import site as admin_site
        from django.utils.datastructures import MultiValueDict
        from unittest.mock import MagicMock

        request = MagicMock()
        request.FILES = MultiValueDict({})  # no files

        form = MagicMock()
        form.instance = self.product

        admin_instance = ProductAdmin(Product, admin_site)
        admin_instance.save_related(request, form, [], True)

        self.assertEqual(ProductPhoto.objects.filter(product=self.product).count(), 0)


# ── Packing slip tests ────────────────────────────────────────────────────────

class PackingSlipTests(TestCase):
    """Packing slip renders for staff only and includes order details."""

    def setUp(self):
        from orders.models import Order
        self.staff = User.objects.create_superuser("admin_sl", "sl@x.com", "AdminPass1!")
        self.regular = User.objects.create_user("user_sl", password="UserPass1!")
        self.order = Order.objects.create(
            full_name="Ali Hassan", phone="03001234567", city="Lahore",
            address="123 Main St", payment_method=Order.Payment.COD,
            subtotal=1000, delivery_fee=250, total=1250,
        )

    def test_staff_can_view_packing_slip(self):
        self.client.force_login(self.staff)
        url = reverse("admin:orders_order_packing_slip", args=[self.order.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.order.number)
        self.assertContains(resp, "Ali Hassan")
        self.assertContains(resp, "Lahore")

    def test_packing_slip_shows_cod_box_for_cod_orders(self):
        self.client.force_login(self.staff)
        url = reverse("admin:orders_order_packing_slip", args=[self.order.pk])
        resp = self.client.get(url)
        self.assertContains(resp, "Collect")
        self.assertContains(resp, "1,250")

    def test_anonymous_cannot_view_packing_slip(self):
        url = reverse("admin:orders_order_packing_slip", args=[self.order.pk])
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    def test_non_staff_cannot_view_packing_slip(self):
        self.client.force_login(self.regular)
        url = reverse("admin:orders_order_packing_slip", args=[self.order.pk])
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)


# ── Bulk import tests ─────────────────────────────────────────────────────────

import openpyxl as _openpyxl


def _make_xlsx(rows, headers=None):
    """Build an in-memory .xlsx with a 'Product Catalog' sheet."""
    if headers is None:
        headers = [
            "", "SKU", "Product Name", "Category", "Short Description",
            "Age Range", "Cost Price (PKR)", "Selling Price (PKR)", "Sale Price (PKR)",
            "Profit (PKR)", "Margin %", "Stock Qty", "Barcode", "Status", "Image File",
        ]
    wb = _openpyxl.Workbook()
    ws = wb.active
    ws.title = "Product Catalog"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _row(name="Test Toy", sku="TST01", category="Sensory play",
         desc="A test toy", age="2-6", cost=300, sell=999, sale=None,
         profit=699, margin=70, stock=10, barcode="", status="Active",
         image_file=""):
    """Return a row tuple matching the default headers."""
    return ("", sku, name, category, desc, age, cost, sell, sale,
            profit, margin, stock, barcode, status, image_file)


class BulkImportParserTests(TestCase):
    """Unit tests for bulk_import.py parser helpers."""

    def test_parse_age_range(self):
        from store.bulk_import import _parse_age
        self.assertEqual(_parse_age("2-6"), (2, 6))
        self.assertEqual(_parse_age("2–6"), (2, 6))   # en dash
        self.assertEqual(_parse_age("0-2"), (0, 2))

    def test_parse_age_6plus(self):
        from store.bulk_import import _parse_age
        self.assertEqual(_parse_age("6+"), (6, 12))

    def test_parse_age_empty_defaults(self):
        from store.bulk_import import _parse_age
        self.assertEqual(_parse_age(None), (1, 6))
        self.assertEqual(_parse_age(""), (1, 6))

    def test_parse_age_invalid_raises(self):
        from store.bulk_import import _parse_age
        with self.assertRaises(ValueError):
            _parse_age("adult")

    def test_cost_barcode_ignored(self):
        from store.bulk_import import _normalize_row, HEADER_MAP
        # Cost Price and Barcode must never be mapped to a field
        self.assertIsNone(HEADER_MAP.get("cost price (pkr)"))
        self.assertIsNone(HEADER_MAP.get("barcode"))
        raw = {
            "product name": "X", "cost price (pkr)": 500,
            "selling price (pkr)": 999, "barcode": "1234567890123",
        }
        canonical = _normalize_row(raw)
        self.assertNotIn("cost_price", canonical)
        self.assertNotIn("barcode", canonical)
        self.assertEqual(canonical.get("selling_price"), 999)


class BulkImportBuildPreviewTests(TestCase):
    """Tests for build_preview (no DB writes)."""

    def setUp(self):
        self.cat = Category.objects.create(name="Sensory play")
        self.staff = User.objects.create_superuser("admin_bi", "bi@x.com", "AdminPass1!")

    def test_create_action_for_new_product(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row()])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(prev.will_create, 1)
        self.assertEqual(prev.will_update, 0)
        self.assertEqual(prev.error_count, 0)
        self.assertEqual(prev.rows[0].action, "create")

    def test_update_action_for_existing_sku(self):
        from store.bulk_import import build_preview
        make_product(self.cat, name="Old Name", price=500)
        Product.objects.filter(name="Old Name").update(
            **{"sku": "TST01"}
        )
        xlsx = _make_xlsx([_row(sku="TST01", name="New Name")])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(prev.will_update, 1)
        self.assertEqual(prev.will_create, 0)

    def test_update_action_for_existing_name(self):
        from store.bulk_import import build_preview
        make_product(self.cat, name="Matching Toy", price=500)
        xlsx = _make_xlsx([_row(name="Matching Toy", sku="")])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(prev.will_update, 1)

    def test_missing_category_error_when_not_ticked(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(category="Ghost Category")])
        prev = build_preview(xlsx, "test.xlsx", create_missing_categories=False,
                             import_as_hidden=True)
        self.assertEqual(prev.error_count, 1)
        self.assertIn("Ghost Category", prev.rows[0].error)

    def test_missing_category_ok_when_ticked(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(category="Brand New Cat")])
        prev = build_preview(xlsx, "test.xlsx", create_missing_categories=True,
                             import_as_hidden=True)
        self.assertEqual(prev.error_count, 0)
        self.assertEqual(prev.will_create, 1)

    def test_sale_price_mapping_preview(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(sell=1000, sale=799)])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        row = prev.rows[0]
        self.assertEqual(row.price, 799)
        self.assertEqual(row.compare_at_price, 1000)

    def test_no_sale_price_when_not_lower(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(sell=1000, sale=1200)])  # sale > sell
        prev = build_preview(xlsx, "test.xlsx", True, True)
        row = prev.rows[0]
        self.assertEqual(row.price, 1000)
        self.assertIsNone(row.compare_at_price)

    def test_preview_saves_nothing(self):
        from store.bulk_import import build_preview
        count_before = Product.objects.count()
        cat_count_before = Category.objects.count()
        xlsx = _make_xlsx([_row(), _row(name="Toy 2", sku="T02")])
        build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(Product.objects.count(), count_before)
        self.assertEqual(Category.objects.count(), cat_count_before)

    def test_missing_product_name_is_error(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(name="")])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(prev.error_count, 1)
        self.assertEqual(prev.will_create, 0)

    def test_bad_age_range_reported(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(age="adult")])
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(prev.error_count, 1)

    def test_hidden_by_default_for_new_products(self):
        from store.bulk_import import build_preview
        xlsx = _make_xlsx([_row(status="Active")])
        prev = build_preview(xlsx, "test.xlsx", True, import_as_hidden=True)
        self.assertFalse(prev.rows[0].is_active)

    def test_preview_rows_property(self):
        from store.bulk_import import build_preview
        rows = [_row(name=f"Toy {i}", sku=f"T{i:02d}") for i in range(25)]
        xlsx = _make_xlsx(rows)
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(len(prev.preview_rows), 20)

    def test_error_rows_property(self):
        from store.bulk_import import build_preview
        rows = [_row(name=f"Toy {i}", sku=f"T{i:02d}") for i in range(5)]
        rows.append(_row(name=""))   # error row
        xlsx = _make_xlsx(rows)
        prev = build_preview(xlsx, "test.xlsx", True, True)
        self.assertEqual(len(prev.error_rows), 1)


class BulkImportExecuteTests(TestCase):
    """Tests for execute_import (writes to DB)."""

    def setUp(self):
        self.cat = Category.objects.create(name="Sensory play")

    def test_creates_new_product(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row()])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertTrue(Product.objects.filter(name="Test Toy").exists())

    def test_new_product_hidden_by_default(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(status="Active")])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        p = Product.objects.get(name="Test Toy")
        self.assertFalse(p.is_active)

    def test_updates_by_sku(self):
        from store.bulk_import import execute_import
        existing = make_product(self.cat, name="Old Name", price=500)
        existing.sku = "TST01"
        existing.save(update_fields=["sku"])
        xlsx = _make_xlsx([_row(sku="TST01", name="New Name", sell=1200)])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["created"], 0)
        existing.refresh_from_db()
        self.assertEqual(existing.price, 1200)

    def test_updates_by_name(self):
        from store.bulk_import import execute_import
        existing = make_product(self.cat, name="Matching Toy", price=500)
        xlsx = _make_xlsx([_row(name="Matching Toy", sku="", sell=888)])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertEqual(result["updated"], 1)
        existing.refresh_from_db()
        self.assertEqual(existing.price, 888)

    def test_sale_price_mapping(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(sell=1000, sale=799)])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        p = Product.objects.get(name="Test Toy")
        self.assertEqual(p.price, 799)
        self.assertEqual(p.compare_at_price, 1000)

    def test_age_6plus_parsed(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(age="6+")])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        p = Product.objects.get(name="Test Toy")
        self.assertEqual(p.age_from, 6)
        self.assertEqual(p.age_to, 12)

    def test_missing_category_creates_when_ticked(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(category="Brand New Category")])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertEqual(result["created"], 1)
        self.assertEqual(len(result["errors"]), 0)
        self.assertTrue(Category.objects.filter(name="Brand New Category").exists())

    def test_missing_category_errors_when_not_ticked(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(category="Ghost Cat")])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": False, "import_as_hidden": True})
        self.assertEqual(result["created"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("Ghost Cat", result["errors"][0])

    def test_needs_assigned_for_new_products(self):
        from store.bulk_import import execute_import
        from store.models import Need
        need = Need.objects.create(name="Strong little hands", slug="strong-little-hands")
        # Category name matches CATEGORY_NEEDS_MAP key "fine motor"
        fine_cat = Category.objects.create(name="Fine motor")
        xlsx = _make_xlsx([_row(category="Fine motor")])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        p = Product.objects.get(name="Test Toy")
        self.assertIn(need, p.needs.all())

    def test_needs_not_changed_for_existing_products(self):
        from store.bulk_import import execute_import
        from store.models import Need
        need = Need.objects.create(name="Strong little hands", slug="strong-little-hands")
        existing = make_product(self.cat, name="Test Toy", price=500)
        existing.sku = "TST01"
        existing.save(update_fields=["sku"])
        existing.needs.add(need)
        # Fine motor category would add "Strong little hands" – but existing product should be unchanged
        fine_cat = Category.objects.create(name="Fine motor")
        xlsx = _make_xlsx([_row(sku="TST01", category="Fine motor")])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        # Needs are unchanged for existing products (they were set before, remain set)
        existing.refresh_from_db()
        self.assertIn(need, existing.needs.all())  # still there, not duplicated

    def test_cost_and_barcode_not_stored(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(cost=500, barcode="9780201379624")])
        execute_import(xlsx, "test.xlsx",
                       {"create_missing_categories": True, "import_as_hidden": True})
        # Product model has no cost/barcode fields – this just verifies no crash
        p = Product.objects.get(name="Test Toy")
        self.assertFalse(hasattr(p, "cost_price"))
        self.assertFalse(hasattr(p, "barcode"))

    def test_slug_is_unique(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([
            _row(name="Same Name", sku="SK1"),
            _row(name="Same Name", sku="SK2"),  # duplicate name, different SKU
        ])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        # First creates, second updates (matched by name)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 1)

    def test_errors_reported_per_row(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([
            _row(name="Good Toy"),
            _row(name=""),          # error: missing name
            _row(name="Bad Age", age="adult"),  # error: unparseable age
        ])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertEqual(result["created"], 1)
        self.assertEqual(len(result["errors"]), 2)

    def test_image_file_map_populated(self):
        from store.bulk_import import execute_import
        xlsx = _make_xlsx([_row(image_file="toy_001.jpg")])
        result = execute_import(xlsx, "test.xlsx",
                                {"create_missing_categories": True, "import_as_hidden": True})
        self.assertIn("toy_001.jpg", result["image_file_map"])
        p = result["image_file_map"]["toy_001.jpg"]
        self.assertEqual(p.name, "Test Toy")


class BulkImportPhotoTests(TestCase):
    """Tests for match_photos_zip."""

    def setUp(self):
        self.cat = Category.objects.create(name="Motor play")
        self.p1 = Product.objects.create(
            category=self.cat, name="Ring Toy", sku="RING1",
            slug="ring-toy", price=999, stock=5, summary="x",
        )
        self.png = _make_png_bytes()

    def _make_zip_with_file(self, filename, data=None):
        buf = io.BytesIO()
        with _zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(filename, data or self.png)
        return buf.getvalue()

    def test_photos_matched_by_image_file(self):
        from store.bulk_import import match_photos_zip
        image_file_map = {"ring.jpg": self.p1}
        zip_bytes = self._make_zip_with_file("ring.jpg")
        result = match_photos_zip(zip_bytes, image_file_map, replace_existing=True)
        self.assertIn("Ring Toy", result["attached"])
        self.p1.refresh_from_db()
        self.assertTrue(bool(self.p1.image))

    def test_no_match_reported(self):
        from store.bulk_import import match_photos_zip
        image_file_map = {"other.jpg": self.p1}
        zip_bytes = self._make_zip_with_file("notmatching.jpg")
        result = match_photos_zip(zip_bytes, image_file_map, replace_existing=True)
        self.assertIn("notmatching.jpg", result["no_match"])

    def test_existing_photo_kept_when_replace_false(self):
        from store.bulk_import import match_photos_zip
        from django.core.files.base import ContentFile
        self.p1.image.save("existing.png", ContentFile(self.png), save=True)
        image_file_map = {"new.jpg": self.p1}
        zip_bytes = self._make_zip_with_file("new.jpg")
        result = match_photos_zip(zip_bytes, image_file_map, replace_existing=False)
        self.assertNotIn("Ring Toy", result["attached"])


class BulkImportViewTests(TestCase):
    """Integration tests for the admin bulk import view."""

    def setUp(self):
        self.staff = User.objects.create_superuser("admin_biv", "biv@x.com", "AdminPass1!")
        self.regular = User.objects.create_user("user_biv", password="UserPass1!")
        self.client.force_login(self.staff)
        self.cat = Category.objects.create(name="Gross motor")

    def test_get_page_loads(self):
        url = reverse("admin:store_product_bulk_import")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk product import")

    def test_anonymous_redirected(self):
        self.client.logout()
        url = reverse("admin:store_product_bulk_import")
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    def test_non_staff_redirected(self):
        self.client.force_login(self.regular)
        url = reverse("admin:store_product_bulk_import")
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    def test_no_file_shows_error(self):
        url = reverse("admin:store_product_bulk_import")
        resp = self.client.post(url, {"action": "preview"})
        self.assertContains(resp, "Please choose")

    def test_preview_post_returns_preview(self):
        url = reverse("admin:store_product_bulk_import")
        xlsx = _make_xlsx([_row(category="Gross motor")])
        f = SimpleUploadedFile("import.xlsx", xlsx,
                               content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp = self.client.post(url, {
            "action": "preview",
            "import_file": f,
            "import_as_hidden": "on",
            "create_missing_categories": "on",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "will create")

    def test_preview_saves_nothing(self):
        url = reverse("admin:store_product_bulk_import")
        count_before = Product.objects.count()
        xlsx = _make_xlsx([_row(category="Gross motor")])
        f = SimpleUploadedFile("import.xlsx", xlsx,
                               content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.client.post(url, {
            "action": "preview",
            "import_file": f,
            "import_as_hidden": "on",
            "create_missing_categories": "on",
        })
        self.assertEqual(Product.objects.count(), count_before)

    def test_confirm_creates_product(self):
        url = reverse("admin:store_product_bulk_import")
        xlsx = _make_xlsx([_row(category="Gross motor")])
        f = SimpleUploadedFile("import.xlsx", xlsx,
                               content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # Step 1: preview
        self.client.post(url, {
            "action": "preview",
            "import_file": f,
            "import_as_hidden": "on",
            "create_missing_categories": "on",
        })
        # Step 2: confirm
        resp = self.client.post(url, {
            "action": "confirm",
            "import_as_hidden": "on",
            "create_missing_categories": "on",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Import complete")
        self.assertTrue(Product.objects.filter(name="Test Toy").exists())

    def test_product_list_changelist_loads(self):
        url = reverse("admin:store_product_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


# ── Chatbot quick button tests ────────────────────────────────────────────────

class QuickButtonTests(TestCase):
    """Tests for chatbot quick-button feature (Part B)."""

    def setUp(self):
        # Reset quick-button state so each test starts from zero.
        BotAnswer.objects.update(show_as_quick=False)
        self.user = User.objects.create_superuser("qbadmin", "qb@test.com", "pass1234x!")

    # ── context processor ────────────────────────────────────────────────────

    def test_context_returns_at_most_six_active_quick_buttons(self):
        for i in range(7):
            BotAnswer.objects.create(
                question=f"Q{i}", keywords=f"kw{i}", answer=f"A{i}",
                show_as_quick=True, active=True, quick_order=i,
            )
        from store.context_processors import store as store_cp
        factory = RequestFactory()
        req = factory.get("/")
        req.session = {}
        ctx = store_cp(req)
        self.assertEqual(len(ctx["bot_quick_buttons"]), 6)

    def test_inactive_quick_button_excluded_from_context(self):
        BotAnswer.objects.create(
            question="Hidden", keywords="hidden", answer="Nope",
            show_as_quick=True, active=False, quick_order=0,
        )
        from store.context_processors import store as store_cp
        factory = RequestFactory()
        req = factory.get("/")
        req.session = {}
        ctx = store_cp(req)
        labels = [b["label"] for b in ctx["bot_quick_buttons"]]
        self.assertNotIn("Hidden", labels)

    def test_context_uses_quick_label_when_set(self):
        BotAnswer.objects.create(
            question="Long question text", keywords="q", answer="A",
            show_as_quick=True, active=True, quick_order=0,
            quick_label="Short label",
        )
        from store.context_processors import store as store_cp
        factory = RequestFactory()
        req = factory.get("/")
        req.session = {}
        ctx = store_cp(req)
        self.assertEqual(ctx["bot_quick_buttons"][0]["label"], "Short label")

    def test_context_falls_back_to_question_when_no_quick_label(self):
        BotAnswer.objects.create(
            question="The question", keywords="q", answer="A",
            show_as_quick=True, active=True, quick_order=0, quick_label="",
        )
        from store.context_processors import store as store_cp
        factory = RequestFactory()
        req = factory.get("/")
        req.session = {}
        ctx = store_cp(req)
        self.assertEqual(ctx["bot_quick_buttons"][0]["label"], "The question")

    # ── quick API endpoint ────────────────────────────────────────────────────

    def test_quick_api_returns_answer(self):
        qa = BotAnswer.objects.create(
            question="Delivery?", keywords="delivery", answer="We deliver.",
            show_as_quick=True, active=True, action="normal",
        )
        url = reverse("store:mila_quick", args=[qa.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["answer"], "We deliver.")
        self.assertEqual(data["action"], "normal")

    def test_quick_api_returns_action_field(self):
        qa = BotAnswer.objects.create(
            question="Find toy", keywords="find", answer="Start finder",
            show_as_quick=True, active=True, action="toy_finder",
        )
        resp = self.client.post(reverse("store:mila_quick", args=[qa.pk]))
        self.assertEqual(resp.json()["action"], "toy_finder")

    def test_quick_api_404_for_inactive(self):
        qa = BotAnswer.objects.create(
            question="Test", keywords="test", answer="Test answer",
            show_as_quick=True, active=False,
        )
        resp = self.client.post(reverse("store:mila_quick", args=[qa.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_quick_api_404_for_non_quick(self):
        qa = BotAnswer.objects.create(
            question="Test", keywords="test", answer="Test answer",
            show_as_quick=False, active=True,
        )
        resp = self.client.post(reverse("store:mila_quick", args=[qa.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_quick_api_requires_post(self):
        qa = BotAnswer.objects.create(
            question="Test", keywords="test", answer="Test answer",
            show_as_quick=True, active=True,
        )
        resp = self.client.get(reverse("store:mila_quick", args=[qa.pk]))
        self.assertEqual(resp.status_code, 405)

    # ── keyword matching still works for non-quick Q&As ──────────────────────

    def test_typed_keyword_matches_non_quick_qa(self):
        BotAnswer.objects.create(
            question="My special question", keywords="unicornkeyword\nspecialkw",
            answer="Yes it works!", show_as_quick=False, active=True,
        )
        url = reverse("store:chat_api")
        resp = self.client.post(
            url,
            data=json.dumps({"message": "unicornkeyword"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["answer"], "Yes it works!")

    # ── admin max-6 enforcement ───────────────────────────────────────────────

    def test_admin_form_rejects_seventh_quick_button(self):
        from store.admin import BotAnswerAdminForm
        for i in range(6):
            BotAnswer.objects.create(
                question=f"Q{i}", keywords=f"kw{i}", answer=f"A{i}",
                show_as_quick=True, active=True, quick_order=i,
            )
        form = BotAnswerAdminForm(data={
            "question": "7th button",
            "keywords": "seventh",
            "answer": "Seven",
            "show_as_quick": True,
            "active": True,
            "action": "normal",
            "quick_order": 6,
            "quick_label": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("show_as_quick", form.errors)
        self.assertIn("Only 6 quick buttons", str(form.errors["show_as_quick"]))

    def test_admin_form_allows_editing_existing_quick_button(self):
        """Saving an already-flagged item (pk already in the 6) must not error."""
        from store.admin import BotAnswerAdminForm
        for i in range(6):
            BotAnswer.objects.create(
                question=f"Q{i}", keywords=f"kw{i}", answer=f"A{i}",
                show_as_quick=True, active=True, quick_order=i,
            )
        existing = BotAnswer.objects.filter(show_as_quick=True).first()
        form = BotAnswerAdminForm(
            data={
                "question": existing.question,
                "keywords": existing.keywords,
                "answer": existing.answer,
                "show_as_quick": True,
                "active": True,
                "action": "normal",
                "quick_order": existing.quick_order,
                "quick_label": "",
            },
            instance=existing,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_botanswer_changelist_loads(self):
        self.client.login(username="qbadmin", password="pass1234x!")
        resp = self.client.get(reverse("admin:store_botanswer_changelist"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "quick buttons active")


# ── RBAC tests ────────────────────────────────────────────────────────────────

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def _make_staff(username, password="pass12345!", **kwargs):
    u = User.objects.create_user(username, password=password, is_staff=True, **kwargs)
    return u


def _assign_role(user, role_name):
    g = Group.objects.get(name=role_name)
    user.groups.set([g])


def _perm(app, codename):
    ct = ContentType.objects.get(app_label=app, model__isnull=False)
    return Permission.objects.filter(codename=codename).first()


class SetupRolesCommandTests(TestCase):
    """setup_roles is idempotent and creates all 10 default groups."""

    def test_creates_all_default_roles(self):
        from store.management.commands.setup_roles import Command
        from store.roles import ROLES
        Command().handle()
        for name in ROLES:
            self.assertTrue(Group.objects.filter(name=name).exists(), f"Missing: {name}")

    def test_idempotent_second_run(self):
        from store.management.commands.setup_roles import Command
        Command().handle()
        count1 = Group.objects.count()
        Command().handle()
        self.assertEqual(Group.objects.count(), count1)

    def test_default_roles_marked_is_default(self):
        from store.management.commands.setup_roles import Command
        from store.models import RoleProfile
        from store.roles import ROLES
        Command().handle()
        for name in ROLES:
            g = Group.objects.get(name=name)
            self.assertTrue(g.profile.is_default, f"{name} not marked is_default")

    def test_custom_role_not_touched(self):
        from store.management.commands.setup_roles import Command
        custom = Group.objects.create(name="Custom Team")
        Command().handle()
        self.assertTrue(Group.objects.filter(name="Custom Team").exists())


class RBACOrderPermissionTests(TestCase):
    """Restricted order views return 403 for users without the right permissions."""

    def setUp(self):
        from store.management.commands.setup_roles import Command
        from orders.models import Order
        Command().handle()
        self.order = Order.objects.create(
            full_name="Test Customer", phone="03001234567", city="Karachi",
            address="1 Main St", payment_method=Order.Payment.COD,
            subtotal=1000, delivery_fee=200, total=1200,
        )

    def test_viewer_cannot_confirm_order(self):
        from orders.models import Order
        staff = _make_staff("viewer1")
        _assign_role(staff, "Viewer")
        self.client.force_login(staff)
        url = reverse("admin:orders_order_change_status",
                      args=[self.order.pk, "confirmed"])
        resp = self.client.get(url)
        # Viewer has no change_order → redirect with error message (still a redirect, not 200)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.CONFIRMED)

    def test_dispatch_role_cannot_confirm_order(self):
        from orders.models import Order
        staff = _make_staff("dispatch1")
        _assign_role(staff, "Dispatch & Delivery")
        self.client.force_login(staff)
        url = reverse("admin:orders_order_change_status",
                      args=[self.order.pk, "confirmed"])
        self.client.get(url)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.CONFIRMED)

    def test_confirm_role_can_confirm_order(self):
        from orders.models import Order
        staff = _make_staff("confirmer1")
        _assign_role(staff, "Order Confirmation")
        self.client.force_login(staff)
        url = reverse("admin:orders_order_change_status",
                      args=[self.order.pk, "confirmed"])
        self.client.get(url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_non_superuser_cannot_delete_order(self):
        from orders.admin import OrderAdmin
        from orders.models import Order as OrderModel
        from django.contrib.admin import site as admin_site
        staff = _make_staff("nodelete1")
        _assign_role(staff, "Manager")
        req = RequestFactory().get("/")
        req.user = staff
        oa = OrderAdmin(OrderModel, admin_site)
        self.assertFalse(oa.has_delete_permission(req))

    def test_superuser_can_delete_order(self):
        from orders.admin import OrderAdmin
        from orders.models import Order as OrderModel
        from django.contrib.admin import site as admin_site
        su = User.objects.create_superuser("supertest1", "su@x.com", "SuperPass1!")
        req = RequestFactory().get("/")
        req.user = su
        oa = OrderAdmin(OrderModel, admin_site)
        self.assertTrue(oa.has_delete_permission(req))


class RBACTherapistTests(TestCase):
    """Therapist Reviewer can only edit the allowed product fields."""

    def setUp(self):
        from store.management.commands.setup_roles import Command
        Command().handle()
        self.therapist = _make_staff("therapist1")
        _assign_role(self.therapist, "Therapist Reviewer")
        cat = make_category("Sensory")
        self.product = make_product(cat, "Test Toy")

    def test_therapist_get_readonly_fields_restricts_non_allowed(self):
        from store.admin import ProductAdmin
        from django.contrib.admin import site as admin_site
        req = RequestFactory().get("/")
        req.user = self.therapist
        pa = ProductAdmin(Product, admin_site)
        ro = pa.get_readonly_fields(req, obj=self.product)
        # Non-allowed fields must be in readonly
        self.assertIn("name", ro)
        self.assertIn("price", ro)

    def test_therapist_allowed_fields_not_readonly(self):
        from store.admin import ProductAdmin
        from django.contrib.admin import site as admin_site
        req = RequestFactory().get("/")
        req.user = self.therapist
        pa = ProductAdmin(Product, admin_site)
        ro = pa.get_readonly_fields(req, obj=self.product)
        # Allowed fields must NOT be read-only
        for f in ProductAdmin.THERAPIST_ALLOWED:
            self.assertNotIn(f, ro, f"{f} should be editable for therapist")

    def test_non_therapist_not_restricted(self):
        from store.admin import ProductAdmin
        from django.contrib.admin import site as admin_site
        su = User.objects.create_superuser("supertest2", "su2@x.com", "SuperPass2!")
        req = RequestFactory().get("/")
        req.user = su
        pa = ProductAdmin(Product, admin_site)
        ro = pa.get_readonly_fields(req, obj=self.product)
        self.assertNotIn("name", ro)


class RBACViewerMaskingTests(TestCase):
    """Viewer sees masked phone/address in the order detail."""

    def setUp(self):
        from store.management.commands.setup_roles import Command
        from orders.models import Order
        Command().handle()
        self.viewer = _make_staff("viewer2")
        _assign_role(self.viewer, "Viewer")
        self.order = Order.objects.create(
            full_name="Ali Khan", phone="03009876543", city="Lahore",
            address="55 Park Ave", payment_method=Order.Payment.COD,
            subtotal=2000, delivery_fee=200, total=2200,
        )

    def test_viewer_fieldset_uses_masked_phone(self):
        from orders.admin import OrderAdmin
        from django.contrib.admin import site as admin_site
        req = RequestFactory().get("/")
        req.user = self.viewer
        oa = OrderAdmin(self.order.__class__, admin_site)
        fs = oa.get_fieldsets(req, self.order)
        customer_fs = next(f for name, f in fs if name == "Customer")
        all_fields = [f for row in customer_fs["fields"] for f in (row if isinstance(row, (list, tuple)) else [row])]
        self.assertIn("masked_phone_ro", all_fields)
        self.assertNotIn("phone", all_fields)

    def test_full_perms_user_sees_real_phone(self):
        from orders.admin import OrderAdmin
        from django.contrib.admin import site as admin_site
        manager = _make_staff("manager1")
        _assign_role(manager, "Manager")
        req = RequestFactory().get("/")
        req.user = manager
        oa = OrderAdmin(self.order.__class__, admin_site)
        fs = oa.get_fieldsets(req, self.order)
        customer_fs = next(f for name, f in fs if name == "Customer")
        all_fields = [f for row in customer_fs["fields"] for f in (row if isinstance(row, (list, tuple)) else [row])]
        self.assertIn("phone", all_fields)


class RBACStaffProfileTests(TestCase):
    """StaffProfileAdmin is superuser-only; is_superuser cannot be set through it."""

    def setUp(self):
        from store.management.commands.setup_roles import Command
        Command().handle()
        self.su = User.objects.create_superuser("su_staff", "su_s@x.com", "SuperPass1!")
        self.regular_staff = _make_staff("reg_staff1")

    def test_non_superuser_cannot_access_staff_list(self):
        self.client.force_login(self.regular_staff)
        resp = self.client.get(reverse("admin:store_staffprofile_changelist"))
        self.assertNotEqual(resp.status_code, 200)

    def test_superuser_can_access_staff_list(self):
        self.client.force_login(self.su)
        resp = self.client.get(reverse("admin:store_staffprofile_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_superuser_not_in_staff_list(self):
        from store.admin import StaffProfileAdmin
        from store.models import StaffProfile
        from django.contrib.admin import site as admin_site
        req = RequestFactory().get("/")
        req.user = self.su
        spa = StaffProfileAdmin(StaffProfile, admin_site)
        qs = spa.get_queryset(req)
        self.assertFalse(qs.filter(is_superuser=True).exists())

    def test_staff_form_sets_is_staff_true(self):
        from store.admin import StaffProfileForm
        data = {
            "username": "newstaff1",
            "first_name": "", "last_name": "",
            "email": "ns@x.com",
            "is_active": True,
            "password1": "NewPass123!",
            "password2": "NewPass123!",
            "role": "",
        }
        form = StaffProfileForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.is_staff)

    def test_staff_form_password_mismatch_errors(self):
        from store.admin import StaffProfileForm
        data = {
            "username": "newstaff2",
            "first_name": "", "last_name": "",
            "email": "ns2@x.com",
            "is_active": True,
            "password1": "NewPass123!",
            "password2": "WrongPass!",
            "role": "",
        }
        form = StaffProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class RBACProxySettingsTests(TestCase):
    """Proxy settings pages redirect to the same StoreSettings row."""

    def setUp(self):
        self.su = User.objects.create_superuser("su_proxy", "sp@x.com", "SuperPass1!")
        self.settings = StoreSettings.objects.create()

    def test_storeinfo_redirects_to_settings_change(self):
        self.client.force_login(self.su)
        resp = self.client.get(reverse("admin:store_storeinfo_changelist"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/{self.settings.pk}/change/", resp["Location"])

    def test_paymentsettings_redirects_to_settings_change(self):
        self.client.force_login(self.su)
        resp = self.client.get(reverse("admin:store_paymentsettings_changelist"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/{self.settings.pk}/change/", resp["Location"])

    def test_non_superuser_cannot_access_storeinfo(self):
        staff = _make_staff("staffproxy1")
        self.client.force_login(staff)
        resp = self.client.get(reverse("admin:store_storeinfo_changelist"))
        self.assertNotEqual(resp.status_code, 200)

    def test_proxy_change_page_loads_for_superuser(self):
        self.client.force_login(self.su)
        resp = self.client.get(
            reverse("admin:store_storeinfo_change", args=[self.settings.pk])
        )
        self.assertEqual(resp.status_code, 200)


# ── Order workflow tests ──────────────────────────────────────────────────────

class OrderWorkflowTests(TestCase):
    """Order workflow: transitions, stock restore, timeline events, bulk actions."""

    def setUp(self):
        from store.management.commands.setup_roles import Command
        Command().handle()
        self.cat = make_category("Test")
        self.product = make_product(self.cat, "Test Toy", price=1000, stock=10)
        self.su = User.objects.create_superuser("workflow_su", "wf@x.com", "Pass1234!")

    def _make_order(self, status="pending"):
        from orders.models import Order, OrderItem
        order = Order.objects.create(
            full_name="Test Customer", phone="03001234567", city="Karachi",
            address="1 Test St", payment_method=Order.Payment.COD,
            subtotal=1000, delivery_fee=200, total=1200, status=status,
        )
        OrderItem.objects.create(order=order, product=self.product,
                                 name=self.product.name, qty=2, price=500)
        return order

    # ── Valid transitions ─────────────────────────────────────────────────────

    def test_valid_transition_pending_to_confirmed(self):
        from orders.models import VALID_TRANSITIONS
        self.assertIn("confirmed", VALID_TRANSITIONS["pending"])

    def test_valid_transition_pending_to_on_hold(self):
        from orders.models import VALID_TRANSITIONS
        self.assertIn("on_hold", VALID_TRANSITIONS["pending"])

    def test_invalid_transition_pending_to_shipped(self):
        from orders.models import VALID_TRANSITIONS
        self.assertNotIn("shipped", VALID_TRANSITIONS["pending"])

    def test_invalid_transition_delivered_to_confirmed(self):
        from orders.models import VALID_TRANSITIONS
        self.assertNotIn("confirmed", VALID_TRANSITIONS["delivered"])

    # ── Stock restore ─────────────────────────────────────────────────────────

    def test_cancel_restores_stock(self):
        order = self._make_order("confirmed")
        before = self.product.stock
        order.cancel_and_restock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, before + 2)

    def test_cancel_sets_stock_restored_flag(self):
        order = self._make_order("confirmed")
        order.cancel_and_restock()
        order.refresh_from_db()
        self.assertTrue(order.stock_restored)

    def test_cancel_only_restores_once(self):
        order = self._make_order("confirmed")
        order.cancel_and_restock()
        self.product.refresh_from_db()
        stock_after_first = self.product.stock
        order.cancel_and_restock()  # second call should be no-op
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_after_first)

    def test_return_restores_stock(self):
        order = self._make_order("shipped")
        before = self.product.stock
        order.return_and_restock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, before + 2)

    def test_return_sets_returned_status(self):
        from orders.models import Order as OrderModel
        order = self._make_order("shipped")
        order.return_and_restock()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderModel.Status.RETURNED)

    def test_return_only_restores_once(self):
        order = self._make_order("shipped")
        order.return_and_restock()
        self.product.refresh_from_db()
        stock_after = self.product.stock
        order.return_and_restock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_after)

    # ── Timeline events ───────────────────────────────────────────────────────

    def test_change_status_view_writes_event(self):
        from orders.models import OrderEvent
        order = self._make_order("pending")
        self.client.force_login(self.su)
        url = reverse("admin:orders_order_change_status", args=[order.pk, "confirmed"])
        self.client.get(url)
        self.assertTrue(OrderEvent.objects.filter(
            order=order, kind=OrderEvent.Kind.STATUS,
            from_value="pending", to_value="confirmed",
        ).exists())

    def test_invalid_transition_rejected_by_view(self):
        from orders.models import Order as OrderModel
        order = self._make_order("pending")
        self.client.force_login(self.su)
        url = reverse("admin:orders_order_change_status", args=[order.pk, "shipped"])
        self.client.get(url)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderModel.Status.PENDING)

    # ── Permission enforcement ────────────────────────────────────────────────

    def test_dispatch_role_cannot_confirm(self):
        from orders.models import Order as OrderModel
        staff = _make_staff("disp_wf1")
        _assign_role(staff, "Dispatch & Delivery")
        order = self._make_order("pending")
        self.client.force_login(staff)
        url = reverse("admin:orders_order_change_status", args=[order.pk, "confirmed"])
        self.client.get(url)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderModel.Status.PENDING)

    def test_confirm_role_cannot_pack(self):
        from orders.models import Order as OrderModel
        staff = _make_staff("conf_wf1")
        _assign_role(staff, "Order Confirmation")
        order = self._make_order("confirmed")
        self.client.force_login(staff)
        url = reverse("admin:orders_order_change_status", args=[order.pk, "packed"])
        self.client.get(url)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderModel.Status.CONFIRMED)

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def test_bulk_confirm_valid_orders(self):
        from orders.models import Order as OrderModel
        o1 = self._make_order("pending")
        o2 = self._make_order("pending")
        self.client.force_login(self.su)
        self.client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "mark_confirmed", "_selected_action": [o1.pk, o2.pk]},
        )
        o1.refresh_from_db()
        o2.refresh_from_db()
        self.assertEqual(o1.status, OrderModel.Status.CONFIRMED)
        self.assertEqual(o2.status, OrderModel.Status.CONFIRMED)

    def test_bulk_confirm_skips_invalid_transitions(self):
        from orders.models import Order as OrderModel
        o1 = self._make_order("pending")
        o2 = self._make_order("shipped")  # can't confirm shipped
        self.client.force_login(self.su)
        self.client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "mark_confirmed", "_selected_action": [o1.pk, o2.pk]},
        )
        o1.refresh_from_db()
        o2.refresh_from_db()
        self.assertEqual(o1.status, OrderModel.Status.CONFIRMED)
        self.assertEqual(o2.status, OrderModel.Status.SHIPPED)

    def test_bulk_cancel_restores_stock(self):
        before = self.product.stock
        o1 = self._make_order("pending")
        o2 = self._make_order("confirmed")
        self.client.force_login(self.su)
        self.client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "cancel_and_restock_action", "_selected_action": [o1.pk, o2.pk]},
        )
        self.product.refresh_from_db()
        # Each order has 2 items, so stock restored by 4
        self.assertEqual(self.product.stock, before + 4)

    # ── Tracking page ─────────────────────────────────────────────────────────

    def test_tracking_page_shows_progress_for_confirmed_order(self):
        order = self._make_order("confirmed")
        resp = self.client.get(reverse("orders:track") + f"?number={order.number}&phone={order.phone}")
        self.assertContains(resp, "Confirmed")

    def test_tracking_page_shows_on_hold_message(self):
        order = self._make_order("on_hold")
        resp = self.client.get(reverse("orders:track") + f"?number={order.number}&phone={order.phone}")
        self.assertContains(resp, "on hold")

    def test_tracking_page_shows_returned_message(self):
        order = self._make_order("returned")
        resp = self.client.get(reverse("orders:track") + f"?number={order.number}&phone={order.phone}")
        self.assertContains(resp, "returned")


class GoogleTranslateTests(TestCase):
    """Google Translate integration: dropdown, cookies, no element.js on normal load."""

    def test_gt_languages_no_duplicate_codes(self):
        from store.languages import GT_LANGUAGES
        codes = [lang[0] for lang in GT_LANGUAGES]
        self.assertEqual(len(codes), len(set(codes)), "Duplicate GT language codes found")

    def test_gt_rtl_flags_are_bool(self):
        from store.languages import GT_LANGUAGES
        for code, native, english, rtl in GT_LANGUAGES:
            self.assertIsInstance(rtl, bool, f"{code} rtl flag should be bool")

    def test_gt_popular_codes_in_gt_languages(self):
        from store.languages import GT_LANGUAGES
        gt_codes = {lang[0] for lang in GT_LANGUAGES}
        popular = ['ur', 'ar', 'hi', 'zh-CN', 'es', 'fr', 'de', 'tr']
        for code in popular:
            self.assertIn(code, gt_codes, f"Popular code {code} not in GT_LANGUAGES")

    def test_element_js_not_in_normal_page_load(self):
        """element.js must NOT appear in the HTML when no lm_gt_lang cookie is set."""
        resp = self.client.get("/")
        self.assertNotContains(resp, "element.js")

    def test_element_js_loaded_when_gt_cookie_set(self):
        """element.js must appear when lm_gt_lang cookie is set."""
        self.client.cookies['lm_gt_lang'] = 'fr'
        resp = self.client.get("/")
        self.assertContains(resp, "element.js")

    def test_gt_dropdown_renders_two_groups(self):
        resp = self.client.get("/")
        self.assertContains(resp, "Popular")
        self.assertContains(resp, "All languages")
        self.assertContains(resp, "lang-gt-list")

    def test_brand_name_has_notranslate(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'notranslate')

    def test_enable_google_translate_false_removes_gt(self):
        from django.test import override_settings
        with override_settings(ENABLE_GOOGLE_TRANSLATE=False):
            resp = self.client.get("/")
            self.assertNotContains(resp, "element.js")
            self.assertNotContains(resp, 'id="lang-gt-list"')

    def test_no_url_changes_with_gt_cookie(self):
        self.client.cookies['lm_gt_lang'] = 'tr'
        for url in ["/", reverse("store:shop"), reverse("orders:track")]:
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])
