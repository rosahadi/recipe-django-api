from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Clean up unverified users with expired verification tokens"

    def handle(self, *args, **options):
        now = timezone.now()
        one_hour_ago = now - timezone.timedelta(hours=1)

        expired_users = User.objects.filter(
            is_active=False, email_verification_sent_at__lt=one_hour_ago
        )

        count = expired_users.count()
        expired_users.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {count} expired unverified users")
        )

        if count == 0:
            self.stdout.write(self.style.WARNING("No expired users found to clean up"))
