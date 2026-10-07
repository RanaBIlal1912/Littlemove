from .cart import Cart
from .models import Category, Need, StoreSettings
from .views import AGE_BANDS


def store(request):
    return {
        "shop": StoreSettings.load(),
        "cart_count": Cart(request).count,
        "nav_categories": Category.objects.filter(is_active=True),
        "nav_ages": AGE_BANDS,
        "nav_needs": Need.objects.filter(is_active=True),
    }
