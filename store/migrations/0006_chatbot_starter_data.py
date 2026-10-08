"""Data migration: add starter BotAnswer and FAQ rows for common questions."""
from django.db import migrations


BOT_ANSWERS = [
    {
        "question": "How long does delivery take?",
        "keywords": "delivery time\nwhen will i receive\nshipping time\narrival\ndays to deliver",
        "answer": (
            "We deliver in 1-2 working days inside Bahawalpur, "
            "and 3-5 working days to all other cities across Pakistan. 🚚"
        ),
    },
    {
        "question": "What is the delivery fee?",
        "keywords": "delivery fee\nshipping cost\nfree delivery\nfree shipping\ncharges\ncost\nfee",
        "answer": (
            "Our standard delivery fee is Rs 200. Orders above Rs 2,000 get FREE delivery! 🎉 "
            "Check the banner on our site for the current free-delivery threshold."
        ),
    },
    {
        "question": "How can I pay?",
        "keywords": "payment\npay\ncod\ncash on delivery\njazzcash\neasypaisa\nhow to pay\npayment method\nbank",
        "answer": (
            "We accept Cash on Delivery (COD), JazzCash, and EasyPaisa. "
            "Choose your preferred method at checkout. 💳"
        ),
    },
    {
        "question": "My item arrived damaged or broken",
        "keywords": "damaged\nbroken\ndefective\nfault\ncracked\nbrake\nnot working\nwrong item",
        "answer": (
            "We're so sorry! Please send a photo of the damaged item on WhatsApp "
            "within 3 days of receiving it and we will sort it out for you immediately. 📸 "
            "WhatsApp: +92 317 3661912"
        ),
    },
    {
        "question": "Can I return a toy?",
        "keywords": "return\nrefund\nexchange\nchange\nback\nreturn policy\nunused",
        "answer": (
            "Unused toys in original packaging can be returned within 7 days. "
            "Contact us on WhatsApp (+92 317 3661912) and we'll arrange a pickup. 📦"
        ),
    },
    {
        "question": "How do I track my order?",
        "keywords": "track\ntracking\norder status\nwhere is my order\nstatus\nmy order",
        "answer": (
            "You can track your order on our website — go to "
            "'Track order' at the top of any page, or visit /track/ and enter your order number. 🔍"
        ),
    },
    {
        "question": "Which toy is right for my child's age?",
        "keywords": "age\nold\nyear\nmonth\nwhich toy\nrecommend\nsuitable\nbest toy\nright toy\nchild age",
        "answer": (
            "Great question! Tell me your child's age and I'll suggest the perfect toy. 🧸 "
            "You can also browse by age group at the top of our shop page."
        ),
    },
    {
        "question": "Talk to a real person on WhatsApp",
        "keywords": "whatsapp\nhuman\nteam\nperson\ntalk\nspeak\ncontact\nhelp\nchat with team",
        "answer": (
            "Of course! Our team is happy to help on WhatsApp. "
            "Send us a message at wa.me/923173661912 (Mon-Sat, 9 am - 9 pm). 💬"
        ),
    },
]

FAQS = [
    {
        "question": "How long does delivery take?",
        "answer": "1-2 working days in Bahawalpur, 3-5 working days to other cities in Pakistan.",
        "order": 1,
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "Cash on Delivery (COD), JazzCash, and EasyPaisa. Choose at checkout.",
        "order": 2,
    },
    {
        "question": "Can I return a toy?",
        "answer": "Yes — unused toys in original packaging within 7 days. Contact us on WhatsApp.",
        "order": 3,
    },
    {
        "question": "What if my item arrives broken or damaged?",
        "answer": "Send us a photo on WhatsApp within 3 days of delivery and we will replace it.",
        "order": 4,
    },
    {
        "question": "Do you offer free delivery?",
        "answer": "Yes! Orders above Rs 2,000 qualify for free delivery across Pakistan.",
        "order": 5,
    },
    {
        "question": "How do I track my order?",
        "answer": "Use the 'Track order' link at the top of any page and enter your order number.",
        "order": 6,
    },
]


def add_starter_data(apps, schema_editor):
    BotAnswer = apps.get_model("store", "BotAnswer")
    FAQ = apps.get_model("store", "FAQ")

    for data in BOT_ANSWERS:
        BotAnswer.objects.get_or_create(
            question=data["question"],
            defaults={"keywords": data["keywords"], "answer": data["answer"]},
        )

    for data in FAQS:
        FAQ.objects.get_or_create(
            question=data["question"],
            defaults={"answer": data["answer"], "order": data["order"]},
        )


def remove_starter_data(apps, schema_editor):
    BotAnswer = apps.get_model("store", "BotAnswer")
    FAQ = apps.get_model("store", "FAQ")
    for data in BOT_ANSWERS:
        BotAnswer.objects.filter(question=data["question"]).delete()
    for data in FAQS:
        FAQ.objects.filter(question=data["question"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0005_homesection_defaults"),
    ]

    operations = [
        migrations.RunPython(add_starter_data, remove_starter_data),
    ]
