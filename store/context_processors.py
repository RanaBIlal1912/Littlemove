import json

from .cart import Cart
from .models import BotAnswer, Category, Need, Popup, StoreSettings
from .views import AGE_BANDS


def store(request):
    quick_qs = (
        BotAnswer.objects
        .filter(show_as_quick=True, active=True)
        .order_by("quick_order")[:6]
    )
    bot_quick_buttons = [
        {
            "id": qa.pk,
            "label": qa.quick_label.strip() or qa.question,
            "action": qa.action,
        }
        for qa in quick_qs
    ]
    return {
        "shop": StoreSettings.load(),
        "cart_count": Cart(request).count,
        "nav_categories": Category.objects.filter(is_active=True),
        "nav_ages": AGE_BANDS,
        "nav_needs": Need.objects.filter(is_active=True),
        "bot_quick_buttons": bot_quick_buttons,
    }


def site_context(request):
    """Extra site-wide context for the redesigned storefront.

    `shop` is already provided by the `store` context processor above, so we
    only add the active popup and the visitor's wishlist count here.
    """
    popup = Popup.get_active()
    if popup is not None and popup.where == Popup.WHERE_HOME:
        if request.resolver_match is None or request.resolver_match.url_name != "home":
            popup = None
    return {
        "popup": popup,
        "wishlist_count": len(request.session.get("wishlist", [])),
    }


def lang_context(request):
    """Inject language list and Google Translate state into every template."""
    from django.conf import settings
    from store.languages import GT_LANGUAGES, GT_RTL_CODES

    gt_lang = request.COOKIES.get('lm_gt_lang', '')

    return {
        'GT_LANGUAGES': GT_LANGUAGES,
        # Comma-separated string for safe data-attribute usage in JS
        'GT_RTL_CODES': ','.join(sorted(GT_RTL_CODES)),
        'ENABLE_GOOGLE_TRANSLATE': getattr(settings, 'ENABLE_GOOGLE_TRANSLATE', True),
        'current_gt_lang': gt_lang,
    }
