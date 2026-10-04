"""Expire unpaid seat holds + pending bookings. Run every minute via cron/Render.

Render: add a Cron Job `python manage.py expire_holds`.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Release expired seat holds and expire linked pending bookings."

    def handle(self, *args, **options):
        from bookings.views import release_expired_holds

        count = release_expired_holds()
        self.stdout.write(self.style.SUCCESS(f"Released {count} expired hold(s)."))
