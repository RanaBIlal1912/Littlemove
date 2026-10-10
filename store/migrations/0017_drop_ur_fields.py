"""
Drop all _ur (Urdu) fields from store models.

These fields were used for hand-translated content in Urdu / Arabic.
The site now uses English only, with Google Website Translator for other
languages. The _ur fields are no longer referenced anywhere in the codebase.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0016_alter_category_options_alter_need_options_and_more"),
    ]

    operations = [
        # Category
        migrations.RemoveField(model_name="category", name="name_ur"),
        migrations.RemoveField(model_name="category", name="description_ur"),
        # Need
        migrations.RemoveField(model_name="need", name="name_ur"),
        migrations.RemoveField(model_name="need", name="description_ur"),
        # Product
        migrations.RemoveField(model_name="product", name="name_ur"),
        migrations.RemoveField(model_name="product", name="summary_ur"),
        migrations.RemoveField(model_name="product", name="description_ur"),
        migrations.RemoveField(model_name="product", name="helps_with_ur"),
        migrations.RemoveField(model_name="product", name="in_the_box_ur"),
        # Banner
        migrations.RemoveField(model_name="banner", name="title_ur"),
        migrations.RemoveField(model_name="banner", name="subtitle_ur"),
        # HomeSection
        migrations.RemoveField(model_name="homesection", name="title_ur"),
        migrations.RemoveField(model_name="homesection", name="subtitle_ur"),
        # FAQ
        migrations.RemoveField(model_name="faq", name="question_ur"),
        migrations.RemoveField(model_name="faq", name="answer_ur"),
        # BotAnswer
        migrations.RemoveField(model_name="botanswer", name="question_ur"),
        migrations.RemoveField(model_name="botanswer", name="answer_ur"),
        migrations.RemoveField(model_name="botanswer", name="quick_label_ur"),
    ]
