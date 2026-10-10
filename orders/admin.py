import csv
from urllib.parse import quote

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    Order, OrderEvent, OrderItem,
    PAYMENT_COLORS, STATUS_COLORS, VALID_TRANSITIONS,
)


def log_event(order, user, kind, from_value="", to_value="", note=""):
    OrderEvent.objects.create(
        order=order, user=user, kind=kind,
        from_value=from_value, to_value=to_value, note=note,
    )


# ── Inlines ─────────────────────────────────────────────────────────────────

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ["name", "sku", "price", "qty", "line_total"]
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    readonly_fields = ["created_at", "actor", "event_desc"]
    fields = readonly_fields
    verbose_name = "Timeline event"
    verbose_name_plural = "Timeline"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description="By")
    def actor(self, obj):
        if obj.user:
            role = obj.user.groups.first()
            rname = f" ({role.name})" if role else ""
            return (obj.user.get_full_name() or obj.user.username) + rname
        return "System"

    @display(description="Event")
    def event_desc(self, obj):
        return obj.describe()


# ── List filters ─────────────────────────────────────────────────────────────

class OrderStatusFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return list(Order.Status.choices) + [("closed", "Cancelled / Returned")]

    def queryset(self, request, qs):
        v = self.value()
        if v == "closed":
            return qs.filter(status__in=["cancelled", "returned"])
        if v and v in dict(Order.Status.choices):
            return qs.filter(status=v)
        return qs


class PaymentTabFilter(admin.SimpleListFilter):
    title = "payment tab"
    parameter_name = "pay_tab"

    def lookups(self, request, model_admin):
        return [("checking", "Payment to check"), ("cod_unpaid", "Unpaid COD")]

    def queryset(self, request, qs):
        if self.value() == "checking":
            return qs.filter(payment_status="checking")
        if self.value() == "cod_unpaid":
            return qs.filter(payment_status="unpaid", payment_method="cod")
        return qs


# ── OrderAdmin ────────────────────────────────────────────────────────────────

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    change_list_template = "admin/orders/order/change_list.html"
    list_display = ["number", "customer_city", "phone_col", "total_rs",
                    "status_badge", "payment_badge", "courier_tracking", "created_at_col"]
    list_filter = [OrderStatusFilter, PaymentTabFilter, "payment_method", "created_at", "city"]
    search_fields = ["number", "full_name", "phone", "tracking_number"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderEventInline]
    readonly_fields = ["number", "created_at", "updated_at", "subtotal", "delivery_fee", "total",
                       "whatsapp_customer", "status_actions", "packing_slip_link",
                       "masked_phone_ro", "masked_address_ro", "cod_paid_action"]
    actions = ["mark_confirmed", "mark_on_hold", "mark_packed", "mark_shipped",
               "mark_delivered", "mark_returned", "mark_paid", "mark_checking",
               "cancel_and_restock_action", "export_orders_csv", "print_packing_slips"]

    # ── Permissions ───────────────────────────────────────────────────────────

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @staticmethod
    def _can_change(request):
        return request.user.is_superuser or request.user.has_perm("orders.change_order")

    @staticmethod
    def _can_see_customer(request):
        return request.user.is_superuser or request.user.has_perm("orders.change_order")

    # ── Dynamic list display ──────────────────────────────────────────────────

    def get_list_display(self, request):
        ld = list(self.list_display)
        if not self._can_see_customer(request):
            ld[ld.index("phone_col")] = "masked_phone_list"
        return ld

    # ── Dynamic actions ───────────────────────────────────────────────────────

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if not request.user.has_perm("orders.confirm_orders"):
                for k in ["mark_confirmed", "mark_on_hold", "cancel_and_restock_action"]:
                    actions.pop(k, None)
            if not request.user.has_perm("orders.dispatch_orders"):
                for k in ["mark_packed", "mark_shipped", "mark_delivered", "mark_returned", "print_packing_slips"]:
                    actions.pop(k, None)
            if not request.user.has_perm("orders.verify_payments"):
                for k in ["mark_paid", "mark_checking"]:
                    actions.pop(k, None)
            if not request.user.has_perm("orders.export_orders"):
                actions.pop("export_orders_csv", None)
        return actions

    # ── Dynamic readonly fields ───────────────────────────────────────────────

    def get_readonly_fields(self, request, obj=None):
        ALWAYS_RO = ["number", "created_at", "updated_at", "subtotal",
                     "delivery_fee", "total", "whatsapp_customer",
                     "status_actions", "packing_slip_link", "cod_paid_action"]
        if request.user.is_superuser:
            return ALWAYS_RO
        editable = set()
        if request.user.has_perm("orders.confirm_orders"):
            editable.update(["status", "internal_note"])
        if request.user.has_perm("orders.dispatch_orders"):
            editable.update(["status", "courier", "tracking_number", "internal_note"])
        if request.user.has_perm("orders.verify_payments"):
            editable.update(["payment_status", "transaction_id"])
        if request.user.has_perm("orders.change_order"):
            editable.add("internal_note")
        ALL_CHANGEABLE = [
            "status", "payment_method", "payment_status", "transaction_id",
            "courier", "tracking_number", "internal_note",
            "full_name", "phone", "email", "city", "address", "notes",
        ]
        extra_ro = [f for f in ALL_CHANGEABLE if f not in editable]
        return ALWAYS_RO + extra_ro + ["masked_phone_ro", "masked_address_ro"]

    # ── Dynamic fieldsets ─────────────────────────────────────────────────────

    def get_fieldsets(self, request, obj=None):
        can_customer = self._can_see_customer(request)
        phone_f = "phone" if can_customer else "masked_phone_ro"
        addr_f  = "address" if can_customer else "masked_address_ro"
        is_su   = request.user.is_superuser

        fs = [
            ("Order", {"fields": [("number", "created_at"), "status_actions", "status"]}),
            ("Customer", {"fields": [
                ("full_name", phone_f), "whatsapp_customer",
                "email", "city", addr_f, "notes",
            ]}),
        ]
        payment_fields = [("payment_method", "payment_status"), ("subtotal", "delivery_fee", "total")]
        if is_su or request.user.has_perm("orders.verify_payments"):
            payment_fields.insert(1, "transaction_id")
        fs.append(("Payment", {"fields": payment_fields}))

        # COD delivered → quick mark-paid button
        if (obj and obj.payment_method == Order.Payment.COD
                and obj.status == Order.Status.DELIVERED
                and obj.payment_status != Order.PaymentStatus.PAID):
            fs.append(("Collect payment", {"fields": ["cod_paid_action"]}))

        if is_su or request.user.has_perm("orders.dispatch_orders"):
            fs.append(("Shipping", {"fields": [("courier", "tracking_number")]}))
        if is_su or request.user.has_perm("orders.change_order"):
            fs.append(("Private", {"fields": ["internal_note"]}))
        fs.append(("Actions", {"fields": ["packing_slip_link"]}))
        return fs

    def change_view(self, request, *args, **kwargs):
        self._current_request = request
        return super().change_view(request, *args, **kwargs)

    # ── Changelist: tab counts ─────────────────────────────────────────────────

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = Order.objects.all()
        tab_params = [
            ("all", "All", None, None),
            ("pending", "New", "status", "pending"),
            ("confirmed", "Confirmed", "status", "confirmed"),
            ("packed", "Packed", "status", "packed"),
            ("shipped", "On the way", "status", "shipped"),
            ("delivered", "Delivered", "status", "delivered"),
            ("on_hold", "On hold", "status", "on_hold"),
            ("closed", "Cancelled / Returned", "status", "closed"),
            ("pay_check", "Payment to check", "pay_tab", "checking"),
            ("cod_unpaid", "Unpaid COD", "pay_tab", "cod_unpaid"),
        ]
        tabs = []
        current_status = request.GET.get("status")
        current_pay_tab = request.GET.get("pay_tab")
        for key, label, param, value in tab_params:
            if key == "all":
                count = qs.count()
                url = request.path
                active = not current_status and not current_pay_tab
            elif key == "closed":
                count = qs.filter(status__in=["cancelled", "returned"]).count()
                url = f"{request.path}?status=closed"
                active = current_status == "closed"
            elif param == "status":
                count = qs.filter(status=value).count()
                url = f"{request.path}?status={value}"
                active = current_status == value
            elif param == "pay_tab":
                if key == "pay_check":
                    count = qs.filter(payment_status="checking").count()
                else:
                    count = qs.filter(payment_status="unpaid", payment_method="cod").count()
                url = f"{request.path}?pay_tab={value}"
                active = current_pay_tab == value
            else:
                count = 0
                url = request.path
                active = False
            tabs.append({"key": key, "label": label, "count": count, "url": url, "active": active})
        extra_context["order_tabs"] = tabs
        return super().changelist_view(request, extra_context=extra_context)

    # ── List display columns ──────────────────────────────────────────────────

    @display(description="Customer / City")
    def customer_city(self, obj):
        return format_html("{}<br><small style='color:#6b7280'>{}</small>",
                           obj.full_name, obj.city)

    @display(description="Phone")
    def phone_col(self, obj):
        return obj.phone

    @display(description="Phone")
    def masked_phone_list(self, obj):
        p = obj.phone or ""
        return p[:3] + "•" * max(0, len(p) - 5) + p[-2:] if len(p) > 5 else "•••"

    @display(description="Total", ordering="total")
    def total_rs(self, obj):
        return f"Rs {obj.total:,}"

    @display(description="Status", ordering="status")
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, "#374151")
        return format_html(
            '<b style="color:{}">{}</b>', color, obj.get_status_display()
        )

    @display(description="Payment", ordering="payment_status")
    def payment_badge(self, obj):
        color = PAYMENT_COLORS.get(obj.payment_status, "#374151")
        return format_html(
            '{}<br><span style="color:{};font-size:.82rem">{}</span>',
            obj.get_payment_method_display(), color, obj.get_payment_status_display(),
        )

    @display(description="Courier / Tracking")
    def courier_tracking(self, obj):
        if obj.courier or obj.tracking_number:
            return format_html("{}<br><small style='color:#6b7280'>{}</small>",
                               obj.courier or "—", obj.tracking_number or "")
        return "—"

    @display(description="Date", ordering="created_at")
    def created_at_col(self, obj):
        return obj.created_at.strftime("%d %b %Y, %I:%M %p") if obj.created_at else "—"

    # ── Detail page display-only fields ──────────────────────────────────────

    @display(description="Change status")
    def status_actions(self, obj):
        if not obj.pk:
            return ""
        req = getattr(self, "_current_request", None)
        is_su = (req is None) or req.user.is_superuser
        can_confirm  = is_su or (req and req.user.has_perm("orders.confirm_orders"))
        can_dispatch = is_su or (req and req.user.has_perm("orders.dispatch_orders"))

        valid_next = VALID_TRANSITIONS.get(obj.status, set())

        BUTTON_SPECS = {
            "confirmed": ("✓ Confirm",         "#dbeafe", "#1e40af", True,  False),
            "on_hold":   ("⏸ On hold",          "#f3f4f6", "#374151", True,  False),
            "packed":    ("📦 Packed",           "#ede9fe", "#5b21b6", False, True),
            "shipped":   ("🚚 Picked up",        "#cffafe", "#0c4a6e", False, True),
            "delivered": ("✅ Delivered",        "#dcfce7", "#166534", False, True),
            "returned":  ("↩ Returned",          "#fff7ed", "#c2410c", False, True),
            "cancelled": ("✕ Cancel & restock",  "#fff0f0", "#b42318", True,  False),
        }
        parts = []
        for val in ["confirmed", "on_hold", "packed", "shipped", "delivered", "returned", "cancelled"]:
            if val not in valid_next:
                continue
            spec = BUTTON_SPECS.get(val)
            if not spec:
                continue
            label, bg, tc, needs_confirm, needs_dispatch = spec
            if needs_confirm and not can_confirm:
                continue
            if needs_dispatch and not can_dispatch:
                continue
            is_cur = obj.status == val
            border = f"2px solid {tc}" if is_cur else "2px solid transparent"
            url = reverse("admin:orders_order_change_status", args=[obj.pk, val])
            parts.append(format_html(
                '<a href="{}" style="display:inline-block;border:{};background:{};color:{};'
                'padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:600;font-size:.85rem">{}</a>',
                url, border, bg, tc, label,
            ))
        if not parts:
            return "—"
        return mark_safe('<div style="display:flex;flex-wrap:wrap;gap:8px;padding:4px 0">'
                         + "".join(str(p) for p in parts) + "</div>")

    @display(description="")
    def cod_paid_action(self, obj):
        if not obj.pk:
            return ""
        url = reverse("admin:orders_order_mark_cod_paid", args=[obj.pk])
        return format_html(
            '<a href="{}" style="display:inline-flex;align-items:center;gap:6px;background:#067647;'
            'color:#fff;padding:9px 18px;border-radius:6px;text-decoration:none;font-weight:600;font-size:.875rem">'
            '💵 Mark cash collected (payment received)</a>',
            url,
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

        status = obj.status
        if status == Order.Status.SHIPPED:
            tracking = ""
            if obj.tracking_number:
                tracking = f" Tracking: {obj.courier or 'courier'} {obj.tracking_number}."
            msg = (f"Hi {obj.full_name}! Your LittleMove order {obj.number} has been picked up "
                   f"by our courier and is on its way to you!{tracking} "
                   f"Expected delivery in 2-4 business days.")
        elif status == Order.Status.DELIVERED:
            msg = (f"Hi {obj.full_name}! Your LittleMove order {obj.number} has been delivered. "
                   f"We hope your little one loves it! Thank you for shopping with LittleMove 🎉")
        elif status == Order.Status.CANCELLED:
            msg = (f"Hi {obj.full_name}, your LittleMove order {obj.number} has been cancelled. "
                   f"Message us if you have any questions.")
        else:
            msg = (f"Hi {obj.full_name}! Your LittleMove order {obj.number} "
                   f"(Rs {obj.total:,}) has been received. "
                   f"We'll be in touch shortly. Thank you for shopping with us!")

        wa_url = f"https://wa.me/{number}?text={quote(msg)}"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" '
            'style="display:inline-flex;align-items:center;gap:6px;background:#25d366;'
            'color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;'
            'font-weight:600;font-size:.875rem">💬 WhatsApp</a>',
            wa_url,
        )

    @display(description="Phone")
    def masked_phone_ro(self, obj):
        p = obj.phone or ""
        return p[:3] + "•" * max(0, len(p) - 5) + p[-2:] if len(p) > 5 else "•••"

    @display(description="Address")
    def masked_address_ro(self, obj):
        return "••• (hidden — requires order-change permission)"

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

    # ── Custom URLs ───────────────────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path as urlpath
        custom = [
            urlpath("<int:order_id>/change-status/<str:status>/",
                    self.admin_site.admin_view(self.change_status_view),
                    name="orders_order_change_status"),
            urlpath("<int:order_id>/packing-slip/",
                    self.admin_site.admin_view(self.packing_slip_view),
                    name="orders_order_packing_slip"),
            urlpath("<int:order_id>/mark-cod-paid/",
                    self.admin_site.admin_view(self.mark_cod_paid_view),
                    name="orders_order_mark_cod_paid"),
            urlpath("bulk-packing-slips/",
                    self.admin_site.admin_view(self.multi_packing_slip_view),
                    name="orders_order_multi_packing_slip"),
        ]
        return custom + super().get_urls()

    def change_status_view(self, request, order_id, status):
        from django.shortcuts import get_object_or_404
        order = get_object_or_404(Order, pk=order_id)
        old_status = order.status

        # Validate transition
        valid = VALID_TRANSITIONS.get(old_status, set())
        if status not in valid:
            messages.error(request, f"Cannot move from {order.get_status_display()} to {status.replace('_', ' ')}.")
            return redirect(reverse("admin:orders_order_change", args=[order_id]))

        # Permission check
        is_su = request.user.is_superuser
        confirm_statuses = {"confirmed", "on_hold", "cancelled"}
        dispatch_statuses = {"packed", "shipped", "delivered", "returned"}

        if status in confirm_statuses:
            if not is_su and not request.user.has_perm("orders.confirm_orders"):
                messages.error(request, "You don't have permission for this action.")
                return redirect(reverse("admin:orders_order_change", args=[order_id]))
        elif status in dispatch_statuses:
            if not is_su and not request.user.has_perm("orders.dispatch_orders"):
                messages.error(request, "You don't have permission for this action.")
                return redirect(reverse("admin:orders_order_change", args=[order_id]))

        # Execute
        if status == "cancelled":
            if order.cancel_and_restock():
                messages.success(request, f"Order {order.number} cancelled — stock restored.")
                log_event(order, request.user, OrderEvent.Kind.STATUS,
                          from_value=old_status, to_value="cancelled")
            else:
                messages.warning(request, f"Order {order.number} was already cancelled.")
        elif status == "returned":
            if order.return_and_restock():
                messages.success(request, f"Order {order.number} marked returned — stock restored.")
                log_event(order, request.user, OrderEvent.Kind.STATUS,
                          from_value=old_status, to_value="returned")
            else:
                messages.warning(request, "Stock was already restored for this order.")
        else:
            order.status = status
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Order {order.number} → {order.get_status_display()}.")
            log_event(order, request.user, OrderEvent.Kind.STATUS,
                      from_value=old_status, to_value=status)

        return redirect(reverse("admin:orders_order_change", args=[order_id]))

    def mark_cod_paid_view(self, request, order_id):
        from django.shortcuts import get_object_or_404
        order = get_object_or_404(Order, pk=order_id)
        if not (request.user.is_superuser or request.user.has_perm("orders.verify_payments")):
            messages.error(request, "Permission denied.")
            return redirect(reverse("admin:orders_order_change", args=[order_id]))
        old = order.payment_status
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=["payment_status", "updated_at"])
        messages.success(request, f"Order {order.number} marked as paid.")
        log_event(order, request.user, OrderEvent.Kind.PAYMENT,
                  from_value=old, to_value=Order.PaymentStatus.PAID)
        return redirect(reverse("admin:orders_order_change", args=[order_id]))

    def packing_slip_view(self, request, order_id):
        from django.shortcuts import get_object_or_404
        order = get_object_or_404(Order, pk=order_id)
        return render(request, "orders/packing_slip.html", {
            "order": order, "items": order.items.all(), "title": f"Packing slip — {order.number}",
        })

    def multi_packing_slip_view(self, request):
        order_ids = request.session.pop("_packing_slip_ids", [])
        orders = Order.objects.prefetch_related("items").filter(pk__in=order_ids)
        return render(request, "orders/packing_slip_bulk.html", {
            "orders": orders, "title": "Packing slips",
        })

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def _bulk_transition(self, request, queryset, new_status, perm):
        if not (request.user.is_superuser or request.user.has_perm(f"orders.{perm}")):
            self.message_user(request, "Permission denied.", level="ERROR")
            return
        done = skipped = 0
        for order in queryset:
            old = order.status
            if new_status not in VALID_TRANSITIONS.get(old, set()):
                skipped += 1
                continue
            if new_status == "cancelled":
                if order.cancel_and_restock():
                    log_event(order, request.user, OrderEvent.Kind.STATUS,
                              from_value=old, to_value="cancelled")
                    done += 1
                else:
                    skipped += 1
            elif new_status == "returned":
                if order.return_and_restock():
                    log_event(order, request.user, OrderEvent.Kind.STATUS,
                              from_value=old, to_value="returned")
                    done += 1
                else:
                    skipped += 1
            else:
                order.status = new_status
                order.save(update_fields=["status", "updated_at"])
                log_event(order, request.user, OrderEvent.Kind.STATUS,
                          from_value=old, to_value=new_status)
                done += 1
        status_label = new_status.replace("_", " ")
        self.message_user(request, f"{done} order(s) marked {status_label}.")
        if skipped:
            self.message_user(request,
                f"{skipped} order(s) skipped (invalid transition for current status).",
                level=messages.WARNING)

    @admin.action(description="Confirm selected (→ Confirmed)")
    def mark_confirmed(self, request, queryset):
        self._bulk_transition(request, queryset, "confirmed", "confirm_orders")

    @admin.action(description="Put on hold")
    def mark_on_hold(self, request, queryset):
        self._bulk_transition(request, queryset, "on_hold", "confirm_orders")

    @admin.action(description="Mark packed")
    def mark_packed(self, request, queryset):
        self._bulk_transition(request, queryset, "packed", "dispatch_orders")

    @admin.action(description="Mark picked up / shipped")
    def mark_shipped(self, request, queryset):
        self._bulk_transition(request, queryset, "shipped", "dispatch_orders")

    @admin.action(description="Mark delivered")
    def mark_delivered(self, request, queryset):
        self._bulk_transition(request, queryset, "delivered", "dispatch_orders")

    @admin.action(description="Mark returned (restores stock)")
    def mark_returned(self, request, queryset):
        self._bulk_transition(request, queryset, "returned", "dispatch_orders")

    @admin.action(description="Cancel and restock selected")
    def cancel_and_restock_action(self, request, queryset):
        self._bulk_transition(request, queryset, "cancelled", "confirm_orders")

    @admin.action(description="Mark payment received (Paid)")
    def mark_paid(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm("orders.verify_payments")):
            self.message_user(request, "Permission denied.", level="ERROR")
            return
        done = 0
        for order in queryset:
            old = order.payment_status
            order.payment_status = Order.PaymentStatus.PAID
            order.save(update_fields=["payment_status", "updated_at"])
            log_event(order, request.user, OrderEvent.Kind.PAYMENT,
                      from_value=old, to_value=Order.PaymentStatus.PAID)
            done += 1
        self.message_user(request, f"{done} order(s) marked paid.")

    @admin.action(description="Mark payment as 'to check'")
    def mark_checking(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm("orders.verify_payments")):
            self.message_user(request, "Permission denied.", level="ERROR")
            return
        done = 0
        for order in queryset:
            old = order.payment_status
            order.payment_status = Order.PaymentStatus.CHECKING
            order.save(update_fields=["payment_status", "updated_at"])
            log_event(order, request.user, OrderEvent.Kind.PAYMENT,
                      from_value=old, to_value=Order.PaymentStatus.CHECKING)
            done += 1
        self.message_user(request, f"{done} order(s) flagged for payment check.")

    @admin.action(description="Export selected orders to CSV")
    def export_orders_csv(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm("orders.export_orders")):
            self.message_user(request, "Permission denied.", level="ERROR")
            return
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="orders.csv"'
        writer = csv.writer(response)
        writer.writerow(["Number", "Date", "Status", "Customer", "Phone", "Email", "City", "Address",
                         "Items", "Subtotal (Rs)", "Delivery (Rs)", "Total (Rs)",
                         "Payment Method", "Payment Status", "Transaction ID", "Courier", "Tracking Number"])
        for order in queryset.prefetch_related("items"):
            writer.writerow([
                order.number, order.created_at.strftime("%Y-%m-%d %H:%M"),
                order.get_status_display(), order.full_name, order.phone, order.email,
                order.city, order.address,
                "; ".join(f"{i.qty}× {i.name}" for i in order.items.all()),
                order.subtotal, order.delivery_fee, order.total,
                order.get_payment_method_display(), order.get_payment_status_display(),
                order.transaction_id, order.courier, order.tracking_number,
            ])
        return response

    @admin.action(description="Print packing slips for selected")
    def print_packing_slips(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm("orders.dispatch_orders")):
            self.message_user(request, "Permission denied.", level="ERROR")
            return
        request.session["_packing_slip_ids"] = list(queryset.values_list("pk", flat=True))
        return redirect(reverse("admin:orders_order_multi_packing_slip"))

    # ── save_model: write events, handle stock restore ────────────────────────

    def save_model(self, request, obj, form, change):
        if not change:
            super().save_model(request, obj, form, change)
            log_event(obj, request.user, OrderEvent.Kind.STATUS,
                      from_value="", to_value=obj.status)
            return

        changed = form.changed_data
        old_status = form.initial.get("status", obj.status)
        old_payment = form.initial.get("payment_status", obj.payment_status)

        if "status" in changed and obj.status == Order.Status.CANCELLED:
            obj.status = old_status
            super().save_model(request, obj, form, change)
            if obj.cancel_and_restock():
                self.message_user(request, "Order cancelled and items put back in stock.")
                log_event(obj, request.user, OrderEvent.Kind.STATUS,
                          from_value=old_status, to_value="cancelled")
        elif "status" in changed and obj.status == Order.Status.RETURNED:
            obj.status = old_status
            super().save_model(request, obj, form, change)
            if obj.return_and_restock():
                self.message_user(request, "Order returned and items put back in stock.")
                log_event(obj, request.user, OrderEvent.Kind.STATUS,
                          from_value=old_status, to_value="returned")
        else:
            super().save_model(request, obj, form, change)
            if "status" in changed:
                log_event(obj, request.user, OrderEvent.Kind.STATUS,
                          from_value=old_status, to_value=obj.status)
            if "payment_status" in changed:
                log_event(obj, request.user, OrderEvent.Kind.PAYMENT,
                          from_value=old_payment, to_value=obj.payment_status)
            if "internal_note" in changed and obj.internal_note.strip():
                log_event(obj, request.user, OrderEvent.Kind.NOTE, note=obj.internal_note)
