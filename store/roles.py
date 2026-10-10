"""
Role definitions and capability→permission mapping for LittleMove.

  python manage.py setup_roles          — create/update defaults (idempotent)

ROLES defines the 10 built-in roles with their permission sets.
ROLE_CAPABILITIES defines the plain-English checkboxes on the Roles page
and maps each checkbox to one or more Django permission codenames.
"""

# ---------------------------------------------------------------------------
# Default roles
# ---------------------------------------------------------------------------

ROLES = {
    "Manager": {
        "description": (
            "Everything operational: products, orders, chatbot, website content. "
            "Cannot change store settings, payment numbers, staff or roles."
        ),
        "permissions": [
            # Orders
            "orders.view_order", "orders.change_order",
            "orders.confirm_orders", "orders.dispatch_orders",
            "orders.verify_payments", "orders.export_orders",
            # Products
            "store.view_product", "store.add_product", "store.change_product",
            "store.view_category", "store.add_category", "store.change_category",
            "store.view_need", "store.add_need", "store.change_need",
            "store.view_productphoto", "store.add_productphoto",
            "store.change_productphoto", "store.delete_productphoto",
            # Website content
            "store.view_homesection", "store.change_homesection",
            "store.view_banner", "store.add_banner", "store.change_banner",
            "store.delete_banner",
            "store.view_popup", "store.add_popup", "store.change_popup",
            "store.view_mediaitem", "store.add_mediaitem",
            "store.change_mediaitem", "store.delete_mediaitem",
            "store.view_testimonial", "store.add_testimonial",
            "store.change_testimonial",
            "store.view_faq", "store.add_faq", "store.change_faq",
            # Chatbot
            "store.view_botanswer", "store.add_botanswer",
            "store.change_botanswer", "store.delete_botanswer",
            "store.view_botsettings", "store.change_botsettings",
            "store.view_chatlog",
        ],
    },
    "Store & Inventory": {
        "description": (
            "Add, edit and manage products, categories, needs and photos. "
            "Bulk import and upload. No access to orders."
        ),
        "permissions": [
            "store.view_product", "store.add_product", "store.change_product",
            "store.view_category", "store.add_category", "store.change_category",
            "store.view_need", "store.add_need", "store.change_need",
            "store.view_productphoto", "store.add_productphoto",
            "store.change_productphoto", "store.delete_productphoto",
        ],
    },
    "Order Confirmation": {
        "description": (
            "View orders; confirm, put on hold or cancel; add internal notes; "
            "use the WhatsApp button. Cannot dispatch or change payments."
        ),
        "permissions": [
            "orders.view_order", "orders.change_order", "orders.confirm_orders",
        ],
    },
    "Dispatch & Delivery": {
        "description": (
            "View orders; mark Packed / Shipped / Delivered; edit courier and "
            "tracking number; print packing slips. Cannot confirm or change payments."
        ),
        "permissions": [
            "orders.view_order", "orders.change_order", "orders.dispatch_orders",
        ],
    },
    "Payments & Accounts": {
        "description": (
            "View orders; change payment status and transaction ID; "
            "export orders to CSV. Cannot change order status."
        ),
        "permissions": [
            "orders.view_order", "orders.change_order",
            "orders.verify_payments", "orders.export_orders",
        ],
    },
    "Helpdesk": {
        "description": (
            "View orders with customer phone; add internal notes; use WhatsApp "
            "button; manage chatbot Q&A, FAQ and testimonials."
        ),
        "permissions": [
            "orders.view_order", "orders.change_order",
            "store.view_botanswer", "store.add_botanswer", "store.change_botanswer",
            "store.view_chatlog",
            "store.view_faq", "store.add_faq", "store.change_faq",
            "store.view_testimonial", "store.add_testimonial", "store.change_testimonial",
        ],
    },
    "Website Content": {
        "description": (
            "Home sections, banners, popup, gallery, testimonials and FAQ. "
            "No access to orders or products."
        ),
        "permissions": [
            "store.view_homesection", "store.change_homesection",
            "store.view_banner", "store.add_banner", "store.change_banner",
            "store.delete_banner",
            "store.view_popup", "store.add_popup", "store.change_popup",
            "store.view_mediaitem", "store.add_mediaitem",
            "store.change_mediaitem", "store.delete_mediaitem",
            "store.view_testimonial", "store.add_testimonial", "store.change_testimonial",
            "store.view_faq", "store.add_faq", "store.change_faq",
        ],
    },
    "Therapist Reviewer": {
        "description": (
            "View products; edit only description, 'helps with', 'in the box', "
            "therapist pick, age range and summary. No orders."
        ),
        "permissions": [
            "store.view_product", "store.change_product",
            "store.view_category",
            "store.view_need",
        ],
    },
    "Order Staff": {
        "description": (
            "All order actions: view, confirm, dispatch, payments, notes, "
            "WhatsApp, packing slip, export. Read-only access to products."
        ),
        "permissions": [
            "orders.view_order", "orders.change_order",
            "orders.confirm_orders", "orders.dispatch_orders",
            "orders.verify_payments", "orders.export_orders",
            "store.view_product",
        ],
    },
    "Viewer": {
        "description": (
            "Read-only access to dashboard, orders and products. "
            "Customer phone and address are masked."
        ),
        "permissions": [
            "orders.view_order",
            "store.view_product",
        ],
    },
}

# ---------------------------------------------------------------------------
# Plain-English checkboxes for the custom Roles admin form
# Each entry: (key, label, [permission codenames granted])
# ---------------------------------------------------------------------------

ROLE_CAPABILITIES = [
    ("orders", "Orders", [
        ("orders_view",
         "View orders",
         ["orders.view_order"]),
        ("orders_customer",
         "See customer phone & address (also required for adding notes)",
         ["orders.view_order", "orders.change_order"]),
        ("orders_confirm",
         "Confirm, hold and cancel orders",
         ["orders.confirm_orders"]),
        ("orders_dispatch",
         "Pack, ship and deliver orders",
         ["orders.dispatch_orders"]),
        ("orders_payments",
         "Change payment status & transaction ID",
         ["orders.verify_payments"]),
        ("orders_export",
         "Export orders to CSV",
         ["orders.export_orders"]),
    ]),
    ("products", "Products", [
        ("products_view",
         "View products",
         ["store.view_product", "store.view_category", "store.view_need"]),
        ("products_edit",
         "Add and edit products (categories, needs)",
         ["store.view_product", "store.add_product", "store.change_product",
          "store.view_category", "store.add_category", "store.change_category",
          "store.view_need", "store.add_need", "store.change_need"]),
        ("products_desc_only",
         "Edit descriptions only — Therapist Reviewer (overrides Add & edit)",
         ["store.view_product", "store.change_product",
          "store.view_category", "store.view_need"]),
        ("products_photos",
         "Manage product photos & bulk tools",
         ["store.view_productphoto", "store.add_productphoto",
          "store.change_productphoto", "store.delete_productphoto"]),
    ]),
    ("web", "Website Content", [
        ("web_pages",
         "Home sections, banners, popup & gallery",
         ["store.view_homesection", "store.change_homesection",
          "store.view_banner", "store.add_banner", "store.change_banner",
          "store.delete_banner",
          "store.view_popup", "store.add_popup", "store.change_popup",
          "store.view_mediaitem", "store.add_mediaitem",
          "store.change_mediaitem", "store.delete_mediaitem"]),
        ("web_reviews",
         "Testimonials & FAQ",
         ["store.view_testimonial", "store.add_testimonial",
          "store.change_testimonial",
          "store.view_faq", "store.add_faq", "store.change_faq"]),
    ]),
    ("bot", "Chatbot & FAQ", [
        ("bot_manage",
         "Manage chatbot Q&A and settings",
         ["store.view_botanswer", "store.add_botanswer",
          "store.change_botanswer", "store.delete_botanswer",
          "store.view_botsettings", "store.change_botsettings"]),
        ("bot_history",
         "View chat history",
         ["store.view_chatlog"]),
        ("bot_faq",
         "Manage FAQ",
         ["store.view_faq", "store.add_faq", "store.change_faq"]),
        ("bot_testimonials",
         "Manage testimonials",
         ["store.view_testimonial", "store.add_testimonial",
          "store.change_testimonial"]),
    ]),
]


# ---------------------------------------------------------------------------
# Helpers used by setup_roles and the admin form
# ---------------------------------------------------------------------------

def _get_permission(full_codename):
    """Return a Permission object by 'app_label.codename'; None if not found."""
    from django.contrib.auth.models import Permission
    try:
        app_label, codename = full_codename.split(".", 1)
        return Permission.objects.get(
            content_type__app_label=app_label, codename=codename
        )
    except (Permission.DoesNotExist, ValueError):
        return None


def permissions_for_codenames(codenames):
    """Return a list of Permission objects for the given list of 'app.codename' strings."""
    perms = []
    for c in codenames:
        p = _get_permission(c)
        if p is not None:
            perms.append(p)
    return perms


def codenames_from_capabilities(capability_keys):
    """Given a list of capability key strings, return the union of permission codenames."""
    key_to_perms = {}
    for _group_key, _group_label, caps in ROLE_CAPABILITIES:
        for key, _label, perm_list in caps:
            key_to_perms[key] = perm_list
    codenames = set()
    for k in capability_keys:
        codenames.update(key_to_perms.get(k, []))
    return list(codenames)
