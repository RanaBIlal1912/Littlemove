"""Dashboard context callback and sidebar badge helpers for the admin."""
import datetime

from django.db.models import Count, Sum
from django.utils import timezone


def dashboard_callback(request, context):
    """Inject KPI data and chart data into the admin index context."""
    from orders.models import Order
    from store.models import Product

    u = request.user
    can_orders = u.is_superuser or u.has_perm("orders.view_order")
    can_products = u.is_superuser or u.has_perm("store.view_product")

    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)
    thirty_days_ago = today - datetime.timedelta(days=29)

    if can_orders:
        context["kpi_orders_today"] = Order.objects.filter(
            created_at__date=today
        ).count()

        context["kpi_revenue_month"] = (
            Order.objects.filter(created_at__date__gte=month_start)
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.RETURNED])
            .aggregate(r=Sum("total"))["r"] or 0
        )

        context["kpi_pending"] = Order.objects.filter(
            status=Order.Status.PENDING
        ).count()

        context["kpi_waiting"] = Order.objects.filter(
            status=Order.Status.PENDING
        ).count()

        context["kpi_ready_ship"] = Order.objects.filter(
            status=Order.Status.PACKED
        ).count()

        context["kpi_on_the_way"] = Order.objects.filter(
            status=Order.Status.SHIPPED
        ).count()

        context["kpi_pay_check"] = Order.objects.filter(
            payment_status=Order.PaymentStatus.CHECKING
        ).count()

        context["kpi_delivered_month"] = Order.objects.filter(
            status=Order.Status.DELIVERED,
            updated_at__date__gte=month_start,
        ).count()

        daily = (
            Order.objects.filter(created_at__date__gte=thirty_days_ago)
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.RETURNED])
            .values("created_at__date")
            .annotate(orders=Count("id"), revenue=Sum("total"))
            .order_by("created_at__date")
        )
        daily_map = {row["created_at__date"]: row for row in daily}

        chart_labels, chart_orders, chart_revenue = [], [], []
        for i in range(30):
            d = thirty_days_ago + datetime.timedelta(days=i)
            chart_labels.append(d.strftime("%b %d"))
            row = daily_map.get(d, {})
            chart_orders.append(row.get("orders", 0))
            chart_revenue.append(row.get("revenue", 0))

        context["chart_labels"] = chart_labels
        context["chart_orders"] = chart_orders
        context["chart_revenue"] = chart_revenue
        context["has_30day_orders"] = sum(chart_orders) > 0
        context["latest_orders"] = (
            Order.objects.select_related().order_by("-created_at")[:10]
        )
    else:
        context["kpi_orders_today"] = None
        context["kpi_revenue_month"] = None
        context["kpi_pending"] = None
        context["kpi_waiting"] = None
        context["kpi_ready_ship"] = None
        context["kpi_on_the_way"] = None
        context["kpi_pay_check"] = None
        context["kpi_delivered_month"] = None
        context["chart_labels"] = []
        context["chart_orders"] = []
        context["chart_revenue"] = []
        context["has_30day_orders"] = False
        context["latest_orders"] = []

    if can_products:
        context["kpi_low_stock"] = Product.objects.filter(
            is_active=True, stock__lte=3
        ).count()
        context["low_stock_products"] = (
            Product.objects.filter(is_active=True, stock__lte=3)
            .order_by("stock", "name")[:10]
        )
        context["no_photo_count"] = Product.objects.filter(
            is_active=True, image=""
        ).count()
    else:
        context["kpi_low_stock"] = None
        context["low_stock_products"] = []
        context["no_photo_count"] = None

    return context


def badge_pending_orders(request):
    from orders.models import Order
    n = Order.objects.filter(status=Order.Status.PENDING).count()
    return str(n) if n else ""


def badge_low_stock(request):
    from store.models import Product
    n = Product.objects.filter(is_active=True, stock__lte=3).count()
    return str(n) if n else ""
