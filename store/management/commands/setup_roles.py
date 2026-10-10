"""Create or update the default LittleMove roles (Django Groups).

    python manage.py setup_roles

This command is idempotent:
  - Creates missing default Groups and their RoleProfiles.
  - Updates permissions on existing default Groups to match roles.py.
  - Never touches custom Groups (is_default=False).
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from store.roles import ROLES, permissions_for_codenames


class Command(BaseCommand):
    help = "Create / update default roles (idempotent, never deletes custom roles)."

    def handle(self, *args, **options):
        from store.models import RoleProfile

        created_count = updated_count = 0

        for name, spec in ROLES.items():
            group, created = Group.objects.get_or_create(name=name)

            profile, _ = RoleProfile.objects.get_or_create(
                group=group,
                defaults={"description": spec["description"], "is_default": True},
            )
            if not created:
                # Update description even if the group already existed
                profile.description = spec["description"]
                profile.is_default = True
                profile.save(update_fields=["description", "is_default"])

            perms = permissions_for_codenames(spec["permissions"])
            group.permissions.set(perms)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created role: {name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  Updated role: {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {created_count} created, {updated_count} updated."
            )
        )
