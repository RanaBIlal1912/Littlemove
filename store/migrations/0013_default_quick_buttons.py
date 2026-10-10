from django.db import migrations


DEFAULTS = [
    {
        "order": 0,
        "question": "Find a toy",
        "keywords": "find toy\nfind a toy\ntoy finder\nrecommend toy\nwhich toy",
        "answer": (
            "I'd love to help you find the perfect toy! "
            "Let me ask a couple of quick questions."
        ),
        "action": "toy_finder",
        "label": "🔍 Find a toy",
        "match_fragments": ["find a toy", "find toy", "toy finder"],
    },
    {
        "order": 1,
        "question": "Delivery & shipping",
        "keywords": (
            "delivery\nshipping\ndeliver\nship\nhow long\nwhen will\nfree delivery"
        ),
        "answer": (
            "We deliver across Pakistan! Orders are dispatched within 1–2 business days. "
            "Free delivery on orders over Rs 3,000. Standard delivery takes 3–5 business days."
        ),
        "action": "normal",
        "label": "🚚 Delivery",
        "match_fragments": ["delivery", "shipping"],
    },
    {
        "order": 2,
        "question": "Payment methods",
        "keywords": (
            "payment\npay\ncash\nonline\ncod\njazzcash\neasypaisa\ncard\nhow to pay"
        ),
        "answer": (
            "We accept Cash on Delivery (COD), JazzCash, Easypaisa, and credit/debit cards. "
            "Payment is collected at delivery for COD orders."
        ),
        "action": "normal",
        "label": "💳 Payment",
        "match_fragments": ["payment method", "how to pay", "jazzcash", "easypaisa"],
    },
    {
        "order": 3,
        "question": "Track my order",
        "keywords": "track\norder status\nwhere is my order\ntracking\nmy order",
        "answer": (
            "You can track your order on our Track Order page. "
            "Go to Menu → Track Order and enter your order number."
        ),
        "action": "normal",
        "label": "📦 Track order",
        "match_fragments": ["track my order", "order status", "where is my order"],
    },
    {
        "order": 4,
        "question": "Return policy",
        "keywords": "return\nrefund\nexchange\nreplace\ncomplaint\ndamaged",
        "answer": (
            "We accept returns within 7 days of delivery for unused items in original packaging. "
            "Contact us on WhatsApp to start a return."
        ),
        "action": "normal",
        "label": "↩️ Returns",
        "match_fragments": ["return policy", "refund", "exchange"],
    },
    {
        "order": 5,
        "question": "Talk to our team",
        "keywords": "whatsapp\ncontact\nhuman\nteam\ntalk\nagent\nsupport",
        "answer": (
            "Connect directly with our team on WhatsApp — we're happy to help!"
        ),
        "action": "whatsapp",
        "label": "💬 WhatsApp",
        "match_fragments": ["talk to our team", "whatsapp", "contact us"],
    },
]


def _find_existing(BotAnswer, fragments):
    for frag in fragments:
        obj = BotAnswer.objects.filter(question__icontains=frag).first()
        if obj:
            return obj
        obj = BotAnswer.objects.filter(keywords__icontains=frag).first()
        if obj:
            return obj
    return None


def create_defaults(apps, schema_editor):
    BotAnswer = apps.get_model("store", "BotAnswer")
    for spec in DEFAULTS:
        existing = _find_existing(BotAnswer, spec["match_fragments"])
        if existing:
            existing.show_as_quick = True
            existing.quick_order = spec["order"]
            existing.action = spec["action"]
            if not existing.quick_label:
                existing.quick_label = spec["label"]
            existing.save(
                update_fields=["show_as_quick", "quick_order", "action", "quick_label"]
            )
        else:
            BotAnswer.objects.create(
                question=spec["question"],
                keywords=spec["keywords"],
                answer=spec["answer"],
                show_as_quick=True,
                quick_label=spec["label"],
                quick_order=spec["order"],
                action=spec["action"],
                active=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_botanswer_quick"),
    ]

    operations = [
        migrations.RunPython(create_defaults, migrations.RunPython.noop),
    ]
