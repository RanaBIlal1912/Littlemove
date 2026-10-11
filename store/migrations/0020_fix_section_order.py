from django.db import migrations


def fix_our_story_order(apps, schema_editor):
    HomeSection = apps.get_model('store', 'HomeSection')
    try:
        our_story = HomeSection.objects.get(type='our_story')
        why_us = HomeSection.objects.get(type='why_us')
        if our_story.order >= why_us.order:
            our_story.order = max(1, why_us.order - 1)
            our_story.save(update_fields=['order'])
    except HomeSection.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0019_botsettings_quick_replies'),
    ]
    operations = [
        migrations.RunPython(fix_our_story_order, migrations.RunPython.noop),
    ]
