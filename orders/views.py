from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from store.cart import Cart

from .forms import PK_CITIES, CheckoutForm, TrackOrderForm
from .models import Order
from .services import OutOfStock, place_order, whatsapp_link

RECENT_ORDERS_KEY = "recent_orders"


def checkout(request):
    cart = Cart(request)
    summary = cart.summary()
    if not summary["lines"]:
        messages.info(request, "Your cart is empty. Add a toy first.")
        return redirect("store:shop")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(form, cart)
            except OutOfStock as exc:
                for name, available in exc.problems:
                    messages.error(request, f"{name}: only {available} left. Please update your cart.")
                return redirect("store:cart")
            recent = request.session.get(RECENT_ORDERS_KEY, [])
            request.session[RECENT_ORDERS_KEY] = (recent + [order.number])[-10:]
            return redirect(order)
    else:
        form = CheckoutForm()

    return render(request, "orders/checkout.html", {**summary, "form": form, "cities": PK_CITIES})


def success(request, number):
    # Only the browser that placed the order can open this page.
    if number not in request.session.get(RECENT_ORDERS_KEY, []):
        raise Http404
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    return render(request, "orders/success.html", {"order": order, "whatsapp_url": whatsapp_link(order)})


STEPS = [Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PACKED,
         Order.Status.SHIPPED, Order.Status.DELIVERED]
STEP_LABELS = {
    Order.Status.PENDING:   "Received",
    Order.Status.CONFIRMED: "Confirmed",
    Order.Status.PACKED:    "Packed",
    Order.Status.SHIPPED:   "On the way",
    Order.Status.DELIVERED: "Delivered",
}


def track(request):
    order = None
    form = TrackOrderForm(request.GET or None)
    if request.GET and form.is_valid():
        order = (Order.objects.prefetch_related("items")
                 .filter(number=form.cleaned_data["number"], phone=form.cleaned_data["phone"]).first())
        if order is None:
            form.add_error(None, "No order matches that number and mobile. Check the SMS or WhatsApp message we sent.")
    steps = []
    is_on_hold = order and order.status == Order.Status.ON_HOLD
    is_returned = order and order.status == Order.Status.RETURNED
    if order and order.status not in (Order.Status.CANCELLED, Order.Status.ON_HOLD):
        current_status = order.status
        if current_status == Order.Status.RETURNED:
            # Show as delivered in the progress bar, but with "Returned" note
            reached = len(STEPS) - 1
        elif current_status in STEPS:
            reached = STEPS.index(current_status)
        else:
            reached = 0
        steps = [{"label": STEP_LABELS[s], "done": i <= reached, "current": i == reached}
                 for i, s in enumerate(STEPS)]
    return render(request, "orders/track.html", {
        "form": form, "order": order, "steps": steps,
        "is_on_hold": is_on_hold,
        "is_returned": is_returned,
    })
