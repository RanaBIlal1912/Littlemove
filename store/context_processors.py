from .cart import Cart
from .models import Category, Need, Popup, StoreSettings
from .views import AGE_BANDS


def store(request):
    return {
        "shop": StoreSettings.load(),
        "cart_count": Cart(request).count,
        "nav_categories": Category.objects.filter(is_active=True),
        "nav_ages": AGE_BANDS,
        "nav_needs": Need.objects.filter(is_active=True),
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
