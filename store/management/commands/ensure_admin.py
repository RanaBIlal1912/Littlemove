"""Create a Django superuser from environment variables if none exists.

    python manage.py ensure_admin

Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and
DJANGO_SUPERUSER_PASSWORD from the environment.  Does nothing (exits
silently) when the env vars are absent or the user already exists.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create admin user from DJANGO_SUPERUSER_* env vars if it does not exist."

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email    = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD not set — skipping.")
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin '{username}' already exists — skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'."))
