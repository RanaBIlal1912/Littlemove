from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ["name", "sku", "price", "qty", "line_total"]
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


STATUS_COLORS = {
    "pending": "#b54708", "confirmed": "#1d4ed8", "packed": "#6941c6",
    "shipped": "#0e7490", "delivered": "#067647", "cancelled": "#667085",
}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "created_at", "full_name", "phone", "total_rs",
                    "payment_badge", "status_badge"]
    list_filter = ["status", "payment_method", "payment_status", "created_at", "city"]
    search_fields = ["number", "full_name", "phone", "email", "transaction_id", "tracking_number"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ["number", "created_at", "updated_at", "subtotal", "delivery_fee", "total",
                       "whatsapp_customer"]
    actions = ["mark_confirmed", "mark_packed", "mark_shipped", "mark_delivered", "mark_paid",
               "cancel_and_restock"]
    fieldsets = [
        ("Order", {"fields": [("number", "created_at"), "status"]}),
        ("Customer", {"fields": [("full_name", "phone"), "whatsapp_customer", "email",
                                 "city", "address", "notes"]}),
        ("Payment", {"fields": [("payment_method", "payment_status"), "transaction_id",
                                ("subtotal", "delivery_fee", "total")]}),
        ("Shipping", {"fields": [("courier", "tracking_number")]}),
        ("Private", {"fields": ["internal_note"]}),
    ]

    @admin.display(description="Total", ordering="total")
    def total_rs(self, obj):
        return f"Rs {obj.total:,}"

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return format_html('<b style="color:{}">{}</b>', STATUS_COLORS.get(obj.status, "#000"),
                           obj.get_status_display())

    @admin.display(description="Payment", ordering="payment_status")
    def payment_badge(self, obj):
        color = {"paid": "#067647", "checking": "#b54708"}.get(obj.payment_status, "#667085")
        return format_html('{}<br><span style="color:{}">{}</span>', obj.get_payment_method_display(),
                           color, obj.get_payment_status_display())

    @admin.display(description="Message customer")
    def whatsapp_customer(self, obj):
        if not obj.phone:
            return "—"
        number = "92" + obj.phone[1:]
        return format_html('<a href="https://wa.me/{}" target="_blank" rel="noopener">Open WhatsApp chat</a>',
                           number)

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
