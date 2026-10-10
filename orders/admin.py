from urllib.parse import quote

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ["name", "sku", "price", "qty", "line_total"]
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


STATUS_COLORS = {
    "pending":   "#b54708",
    "confirmed": "#1d4ed8",
    "packed":    "#6941c6",
    "shipped":   "#0e7490",
    "delivered": "#067647",
    "cancelled": "#667085",
}


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ["number", "created_at", "full_name", "city", "phone",
                    "total_rs", "payment_badge", "cod_amount", "status_badge"]
    list_filter = ["status", "payment_method", "payment_status", "created_at", "city"]
    search_fields = ["number", "full_name", "phone", "email", "transaction_id", "tracking_number"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ["number", "created_at", "updated_at", "subtotal", "delivery_fee", "total",
                       "whatsapp_customer", "status_actions", "packing_slip_link"]
    actions = ["mark_confirmed", "mark_packed", "mark_shipped", "mark_delivered", "mark_paid",
               "cancel_and_restock"]
    fieldsets = [
        ("Order", {"fields": [("number", "created_at"), "status_actions", "status"]}),
        ("Customer", {"fields": [("full_name", "phone"), "whatsapp_customer", "email",
                                 "city", "address", "notes"]}),
        ("Payment", {"fields": [("payment_method", "payment_status"), "transaction_id",
                                ("subtotal", "delivery_fee", "total")]}),
        ("Shipping", {"fields": [("courier", "tracking_number")]}),
        ("Private", {"fields": ["internal_note"]}),
        ("Actions", {"fields": ["packing_slip_link"]}),
    ]

    # ── List display columns ───────────────────────────────────────────────────

    @display(description="Total", ordering="total")
    def total_rs(self, obj):
        return f"Rs {obj.total:,}"

    @display(description="COD amount")
    def cod_amount(self, obj):
        if obj.payment_method == Order.Payment.COD:
            return f"Rs {obj.total:,}"
        return "—"

    @display(description="Status", ordering="status")
    def status_badge(self, obj):
        return format_html(
            '<b style="color:{}">{}</b>',
            STATUS_COLORS.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    @display(description="Payment", ordering="payment_status")
    def payment_badge(self, obj):
        color = {"paid": "#067647", "checking": "#b54708"}.get(obj.payment_status, "#667085")
        return format_html(
            '{}<br><span style="color:{}">{}</span>',
            obj.get_payment_method_display(),
            color,
            obj.get_payment_status_display(),
        )

    # ── Detail page readonly fields ────────────────────────────────────────────

    @display(description="Change status")
    def status_actions(self, obj):
        if not obj.pk:
            return ""
        STEPS = [
            ("confirmed", "✓ Confirm",   "#dbeafe", "#1e40af"),
            ("packed",    "📦 Packed",   "#ede9fe", "#5b21b6"),
            ("shipped",   "🚚 Shipped",  "#cffafe", "#0c4a6e"),
            ("delivered", "✅ Delivered","#dcfce7", "#166534"),
        ]
        parts = []
        for val, label, bg, tc in STEPS:
            is_cur = obj.status == val
            border = f"2px solid {tc}" if is_cur else "2px solid transparent"
            url = reverse("admin:orders_order_change_status", args=[obj.pk, val])
            parts.append(format_html(
                '<a href="{}" style="display:inline-block;border:{};background:{};color:{};'
                'padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:600;font-size:.85rem">'
                '{}</a>',
                url, border, bg, tc, label,
            ))
        if obj.status != "cancelled":
            cancel_url = reverse("admin:orders_order_change_status", args=[obj.pk, "cancel"])
            parts.append(format_html(
                '<a href="{}" style="display:inline-block;border:2px solid #fca5a5;background:#fff0f0;'
                'color:#b42318;padding:8px 16px;border-radius:6px;text-decoration:none;'
                'font-weight:600;font-size:.85rem">✕ Cancel &amp; restock</a>',
                cancel_url,
            ))
        inner = mark_safe("".join(str(p) for p in parts))
        return mark_safe(
            '<div style="display:flex;flex-wrap:wrap;gap:8px;padding:4px 0">' + str(inner) + "</div>"
        )

    @display(description="Message customer")
    def whatsapp_customer(self, obj):
        if not obj.phone:
            return "—"
        phone = obj.phone.strip()
        if phone.startswith("0"):
            number = "92" + phone[1:]
        elif phone.startswith("+"):
            number = phone[1:].replace(" ", "")
        else:
            number = phone
        msg = (
            f"Hi {obj.full_name}! Your LittleMove order {obj.number} "
            f"(Rs {obj.total:,}) has been received. "
            f"We'll be in touch shortly. Thank you for shopping with us!"
        )
        wa_url = f"https://wa.me/{number}?text={quote(msg)}"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" '
            'style="display:inline-flex;align-items:center;gap:6px;background:#25d366;'
            'color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;'
            'font-weight:600;font-size:.875rem">💬 WhatsApp</a>',
            wa_url,
        )

    @display(description="")
    def packing_slip_link(self, obj):
        if not obj.pk:
            return ""
        url = reverse("admin:orders_order_packing_slip", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" '
            'style="display:inline-flex;align-items:center;gap:6px;background:#f3f4f6;'
            'color:#374151;border:1px solid #d1d5db;padding:7px 14px;border-radius:6px;'
            'text-decoration:none;font-weight:600;font-size:.875rem">🖨 Print packing slip</a>',
            url,
        )

    # ── Custom URLs ────────────────────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path as urlpath
        custom = [
            urlpath(
                "<int:order_id>/change-status/<str:status>/",
                self.admin_site.admin_view(self.change_status_view),
                name="orders_order_change_status",
            ),
            urlpath(
                "<int:order_id>/packing-slip/",
                self.admin_site.admin_view(self.packing_slip_view),
                name="orders_order_packing_slip",
            ),
        ]
        return custom + super().get_urls()

    def change_status_view(self, request, order_id, status):
        from django.shortcuts import get_object_or_404, redirect
        order = get_object_or_404(Order, pk=order_id)
        VALID = {s.value for s in Order.Status}
        if status == "cancel":
            if order.cancel_and_restock():
                messages.success(request, f"Order {order.number} cancelled — stock restored.")
            else:
                messages.warning(request, f"Order {order.number} was already cancelled.")
        elif status in VALID and order.status != Order.Status.CANCELLED:
            order.status = status
            order.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                f"Order {order.number} → {Order.Status(status).label}.",
            )
        return redirect(reverse("admin:orders_order_change", args=[order_id]))

    def packing_slip_view(self, request, order_id):
        from django.shortcuts import get_object_or_404, render
        order = get_object_or_404(Order, pk=order_id)
        context = {
            "order": order,
            "items": order.items.all(),
            "title": f"Packing slip — {order.number}",
        }
        return render(request, "orders/packing_slip.html", context)

    # ── Bulk actions ───────────────────────────────────────────────────────────

    def _set_status(self, request, queryset, status):
        updated = queryset.exclude(status=Order.Status.CANCELLED).update(status=status)
        self.message_user(request, f"{updated} order(s) marked {Order.Status(status).label.lower()}.")

    @admin.action(description="Mark confirmed")
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CONFIRMED)

    @admin.action(description="Mark packed")
    def mark_packed(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PACKED)

    @admin.action(description="Mark shipped")
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description="Mark delivered")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED)

    @admin.action(description="Mark payment received")
    def mark_paid(self, request, queryset):
        n = queryset.update(payment_status=Order.PaymentStatus.PAID)
        self.message_user(request, f"{n} order(s) marked paid.")

    @admin.action(description="Cancel and put items back in stock")
    def cancel_and_restock(self, request, queryset):
        done = sum(1 for order in queryset if order.cancel_and_restock())
        skipped = queryset.count() - done
        self.message_user(request, f"{done} order(s) cancelled and restocked.")
        if skipped:
            self.message_user(request, f"{skipped} were already cancelled.", messages.WARNING)

    def has_add_permission(self, request):
        return False  # orders come from the website checkout

    def save_model(self, request, obj, form, change):
        cancelling = change and "status" in form.changed_data and obj.status == Order.Status.CANCELLED
        if cancelling:
            obj.status = form.initial["status"]  # let cancel_and_restock do the switch
        super().save_model(request, obj, form, change)
        if cancelling and obj.cancel_and_restock():
            self.message_user(request, "Order cancelled and items put back in stock.")

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.status == Order.Status.CANCELLED:
            ro.append("status")  # use the action; reopening must not double-count stock
        return ro
