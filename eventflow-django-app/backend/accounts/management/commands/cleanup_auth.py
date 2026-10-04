"""Clean expired verification codes + used reset tokens. Run daily via cron."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Delete expired email-verification codes and old password-reset tokens."

    def handle(self, *args, **options):
        from accounts.models import EmailVerification, PasswordResetToken

        now = timezone.now()
        codes, _ = EmailVerification.objects.filter(expires_at__lt=now - timedelta(days=1)).delete()
        tokens, _ = PasswordResetToken.objects.filter(
            expires_at__lt=now - timedelta(days=1)).delete()
        self.stdout.write(self.style.SUCCESS(f"Cleaned {codes} code(s), {tokens} token(s)."))
