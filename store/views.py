import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .models import (
    Banner, Bundle, Category, HomeSection, MediaItem, Need, OurStory,
    Product, Testimonial,
)
from .templatetags.store_tags import illus as _illus


def _item_json(line):
    """Serialise one cart line for the AJAX drawer JSON."""
    has_img = bool(line.product.image)
    return {
        "pid": line.product.pk,
        "name": line.product.name,
        "qty": line.qty,
        "price": float(line.product.price),
        "line_total": float(line.line_total),
        "url": line.product.get_absolute_url(),
        "image": line.product.image.url if has_img else None,
        "illustration_svg": str(_illus(line.product.illustration)) if not has_img else None,
    }

SORTS = {
    "new": ("Newest", "-created_at"),
    "price-low": ("Price: low to high", "price"),
    "price-high": ("Price: high to low", "-price"),
    "name": ("Name", "name"),
}
AGE_BANDS = {
    "0-2": ("0–2 years", 0, 2),
    "2-4": ("2–4 years", 2, 4),
    "4-6": ("4–6 years", 4, 6),
    "6+": ("6+ years", 6, 99),
}
PRICE_CAPS = [1000, 2000, 3000, 5000]


def home(request):
    live = Product.objects.live().select_related("category")
    total_live = live.count()
    # Cap at 3 product rows when the shop has fewer than 30 products.
    MAX_ROWS = 3 if total_live < 30 else 10

    shown = set()
    rows_shown = [0]

    def pick_row(candidates, cap=8):
        """Return up to *cap* items not already shown; return [] if fewer than 4 remain."""
        if rows_shown[0] >= MAX_ROWS:
            return []
        items = [p for p in candidates if p.pk not in shown][:cap]
        if len(items) >= 4:
            shown.update(p.pk for p in items)
            rows_shown[0] += 1
            return items
        return []

    feat_qs = list(live.filter(is_featured=True)[:8]) or list(live[:8])
    featured = pick_row(feat_qs)

    on_sale_all = [p for p in live.filter(compare_at_price__isnull=False, stock__gt=0) if p.on_sale]
    on_sale = pick_row(on_sale_all)

    # Fetch a bit more than 8 so deduplication still yields a full row
    new_all = list(live.order_by("-created_at")[:len(shown) + 9])
    new_arrivals = pick_row(new_all)

    picks_all = list(live.filter(therapist_pick=True)[:len(shown) + 9])
    picks = pick_row(picks_all)

    sections = {s.type: s for s in HomeSection.objects.all()}
    bundles = Bundle.objects.filter(active=True).prefetch_related("products")
    our_story = OurStory.load()

    return render(request, "store/home.html", {
        "banners": Banner.objects.filter(is_active=True),
        "categories": Category.objects.filter(is_active=True),
        "needs": Need.objects.filter(is_active=True),
        "featured": featured,
        "on_sale": on_sale,
        "new_arrivals": new_arrivals,
        "picks": picks,
        "testimonials": Testimonial.objects.filter(is_active=True)[:6],
        "age_bands": AGE_BANDS,
        "price_caps": PRICE_CAPS,
        "sections": sections,
        "section_order": list(HomeSection.objects.values_list("type", flat=True)),
        "bundles": bundles,
        "our_story": our_story,
    })


def shop(request):
    products = Product.objects.live().select_related("category")
    category = None
    if slug := request.GET.get("category"):
        category = Category.objects.filter(slug=slug, is_active=True).first()
        if category is None:  # old or renamed link: show all toys instead of an error
            return redirect("store:shop")
        products = products.filter(category=category)

    need = None
    if nslug := request.GET.get("need"):
        need = Need.objects.filter(slug=nslug, is_active=True).first()
        if need is None:
            return redirect("store:shop")
        products = products.filter(needs=need)

    age = request.GET.get("age")
    if age in AGE_BANDS:
        _, lo, hi = AGE_BANDS[age]
        products = products.filter(age_from__lt=hi, age_to__gte=lo)

    q = (request.GET.get("q") or "").strip()[:60]
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(summary__icontains=q) | Q(helps_with__icontains=q)
            | Q(category__name__icontains=q)
        )

    if request.GET.get("instock"):
        products = products.filter(stock__gt=0)

    on_sale = bool(request.GET.get("sale"))
    if on_sale:
        products = products.filter(compare_at_price__isnull=False, compare_at_price__gt=F("price"))

    picks = bool(request.GET.get("pick"))
    if picks:
        products = products.filter(therapist_pick=True)

    max_price = request.GET.get("max")
    max_price = int(max_price) if (max_price or "").isdigit() else None
    if max_price:
        products = products.filter(price__lte=max_price)

    sort = request.GET.get("sort", "new")
    if sort not in SORTS:
        sort = "new"
    products = products.order_by(SORTS[sort][1], "pk")

    page = Paginator(products, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "store/shop.html", {
        "page": page,
        "category": category,
        "need": need,
        "needs": Need.objects.filter(is_active=True),
        "q": q,
        "age": age,
        "sort": sort,
        "sorts": SORTS,
        "age_bands": AGE_BANDS,
        "price_caps": PRICE_CAPS,
        "max_price": max_price,
        "on_sale": on_sale,
        "picks": picks,
        "categories": Category.objects.filter(is_active=True),
        "querystring": params.urlencode(),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.live().select_related("category"), slug=slug)
    related = (Product.objects.live().filter(category=product.category)
               .exclude(pk=product.pk).select_related("category")[:8])
    in_cart = Cart(request).data.get(str(product.pk), 0)
    return render(request, "store/product.html", {
        "product": product, "related": related, "in_cart": in_cart,
        "photos": product.photos.all(),
    })


def product_quickview(request, slug):
    """Minimal product card rendered inside the quick-view modal."""
    product = get_object_or_404(Product.objects.live().select_related("category"), slug=slug)
    return render(request, "store/_quickview.html", {
        "product": product, "photos": product.photos.all(),
    })


def gallery(request):
    items = MediaItem.objects.filter(show_in_gallery=True).order_by("order")
    return render(request, "store/gallery.html", {"items": items})


def search_suggest(request):
    """JSON autocomplete used by the header search box."""
    q = (request.GET.get("q") or "").strip()[:40]
    if len(q) < 2:
        return JsonResponse({"results": []})
    products = (Product.objects.live()
                .filter(Q(name__icontains=q) | Q(category__name__icontains=q))
                .select_related("category")[:8])
    results = [{
        "name": p.name,
        "price": p.price,
        "url": p.get_absolute_url(),
        "image": p.image.url if p.image else None,
        "category": p.category.name,
    } for p in products]
    return JsonResponse({"results": results})


def wishlist_toggle(request, product_id):
    """Add/remove a product id in the session wishlist. Returns JSON."""
    wl = request.session.get("wishlist", [])
    try:
        pid = int(product_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "bad id"}, status=400)
    if not Product.objects.live().filter(pk=pid).exists():
        return JsonResponse({"error": "not found"}, status=404)
    if pid in wl:
        wl.remove(pid)
        added = False
    else:
        wl.append(pid)
        added = True
    request.session["wishlist"] = wl
    request.session.modified = True
    return JsonResponse({"added": added, "count": len(wl)})


def wishlist_view(request):
    pids = request.session.get("wishlist", [])
    products = list(Product.objects.live().select_related("category").filter(pk__in=pids))
    return render(request, "store/wishlist.html", {"products": products})


def _back(request, fallback="store:cart"):
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect(fallback)


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product.objects.live(), pk=product_id)
    cart = Cart(request)
    try:
        qty = max(1, int(request.POST.get("qty", 1)))
    except ValueError:
        qty = 1
    if not product.in_stock:
        messages.error(request, f"{product.name} is sold out right now.")
        return _back(request, product.get_absolute_url())
    before = cart.data.get(str(product.pk), 0)
    cart.add(product, qty)
    after = cart.data.get(str(product.pk), 0)
    if after - before < qty:
        messages.warning(request, f"Only {product.stock} of {product.name} available — your cart has {after}.")
    else:
        messages.success(request, f"Added {product.name} to your cart.")

    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json and not request.POST.get("buy_now"):
        summary = cart.summary()
        return JsonResponse({
            "ok": True,
            "cart_count": cart.count,
            "message": f"Added {product.name} to cart",
            "items": [_item_json(line) for line in summary["lines"]],
            "subtotal": summary["subtotal"],
            "delivery": summary["delivery"],
            "total": summary["total"],
            "to_free_delivery": summary["to_free_delivery"],
        })

    if request.POST.get("buy_now"):
        return redirect("orders:checkout")
    return _back(request, product.get_absolute_url())


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = Product.objects.live().filter(pk=product_id).first()
    if product is None:
        cart.remove(product_id)
    else:
        try:
            qty = int(request.POST.get("qty", 1))
        except ValueError:
            qty = 1
        cart.set(product, qty)
    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json:
        summary = cart.summary()
        return JsonResponse({
            "ok": True,
            "cart_count": cart.count,
            "items": [_item_json(line) for line in summary["lines"]],
            "subtotal": summary["subtotal"],
            "delivery": summary["delivery"],
            "total": summary["total"],
            "to_free_delivery": summary["to_free_delivery"],
        })
    return redirect("store:cart")


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    messages.info(request, "Removed from your cart.")
    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json:
        cart = Cart(request)
        summary = cart.summary()
        return JsonResponse({
            "ok": True,
            "cart_count": cart.count,
            "items": [_item_json(line) for line in summary["lines"]],
            "subtotal": summary["subtotal"],
            "delivery": summary["delivery"],
            "total": summary["total"],
            "to_free_delivery": summary["to_free_delivery"],
        })
    return redirect("store:cart")


def cart_view(request):
    return render(request, "store/cart.html", Cart(request).summary())


def delivery_info(request):
    return render(request, "store/delivery.html")


def bundle_detail(request, slug):
    bundle = get_object_or_404(Bundle, slug=slug, active=True)
    products = bundle.products.filter(is_active=True, category__is_active=True).select_related("category")
    return render(request, "store/bundle.html", {
        "bundle": bundle,
        "products": products,
    })


@require_POST
def bundle_add_to_cart(request, bundle_id):
    bundle = get_object_or_404(Bundle, pk=bundle_id, active=True)
    cart = Cart(request)
    added = []
    for product in bundle.products.filter(is_active=True, category__is_active=True, stock__gt=0):
        cart.add(product, 1)
        added.append(product.name)
    if added:
        messages.success(request, f"Added {bundle.name} to your cart ({len(added)} items).")
    else:
        messages.warning(request, f"All items in {bundle.name} are currently out of stock.")
    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json:
        summary = cart.summary()
        return JsonResponse({
            "ok": True,
            "cart_count": cart.count,
            "items": [_item_json(line) for line in summary["lines"]],
            "subtotal": summary["subtotal"],
            "delivery": summary["delivery"],
            "total": summary["total"],
            "to_free_delivery": summary["to_free_delivery"],
        })
    return redirect("store:bundle_detail", slug=bundle.slug)


@require_POST
def chat_api(request):
    """Handle chatbot messages from the Mila widget."""
    try:
        data = json.loads(request.body)
        user_message = str(data.get("message", "")).strip()[:500]
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    from .chatbot import get_bot_response
    result = get_bot_response(request, user_message)
    return JsonResponse(result)
