"""Dashboard context callback and sidebar badge helpers for the admin."""
import datetime

from django.db.models import Count, Sum
from django.utils import timezone


def dashboard_callback(request, context):
    """Inject KPI data and chart data into the admin index context."""
    from orders.models import Order
    from store.models import Product

    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)
    thirty_days_ago = today - datetime.timedelta(days=29)

    # KPI cards
    context["kpi_orders_today"] = Order.objects.filter(
        created_at__date=today
    ).count()

    context["kpi_revenue_month"] = (
        Order.objects.filter(
            created_at__date__gte=month_start,
        ).exclude(status=Order.Status.CANCELLED)
        .aggregate(r=Sum("total"))["r"] or 0
    )

    context["kpi_pending"] = Order.objects.filter(
        status=Order.Status.PENDING
    ).count()

    context["kpi_low_stock"] = Product.objects.filter(
        is_active=True, stock__lte=3
    ).count()

    # 30-day chart: daily orders and revenue
    daily = (
        Order.objects.filter(
            created_at__date__gte=thirty_days_ago,
        ).exclude(status=Order.Status.CANCELLED)
        .values("created_at__date")
        .annotate(orders=Count("id"), revenue=Sum("total"))
        .order_by("created_at__date")
    )
    daily_map = {row["created_at__date"]: row for row in daily}

    chart_labels = []
    chart_orders = []
    chart_revenue = []
    for i in range(30):
        d = thirty_days_ago + datetime.timedelta(days=i)
        chart_labels.append(d.strftime("%b %d"))
        row = daily_map.get(d, {})
        chart_orders.append(row.get("orders", 0))
        chart_revenue.append(row.get("revenue", 0))

    context["chart_labels"] = chart_labels
    context["chart_orders"] = chart_orders
    context["chart_revenue"] = chart_revenue

    # Latest 10 orders
    context["latest_orders"] = (
        Order.objects.select_related()
        .order_by("-created_at")[:10]
    )

    # Low stock list
    context["low_stock_products"] = (
        Product.objects.filter(is_active=True, stock__lte=3)
        .order_by("stock", "name")[:10]
    )

    # Products with no main photo
    context["no_photo_count"] = Product.objects.filter(is_active=True, image="").count()

    # Whether the 30-day chart has any data
    context["has_30day_orders"] = sum(chart_orders) > 0

    return context


def badge_pending_orders(request):
    from orders.models import Order
    n = Order.objects.filter(status=Order.Status.PENDING).count()
    return str(n) if n else ""


def badge_low_stock(request):
    from store.models import Product
    n = Product.objects.filter(is_active=True, stock__lte=3).count()
    return str(n) if n else ""
