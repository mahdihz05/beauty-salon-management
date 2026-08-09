from django.core.management.base import BaseCommand

from bookings.engine import expire_stale_holds


class Command(BaseCommand):
    help = "رزروهای موقت منقضی‌شده را لغو و اسلات آن‌ها را آزاد می‌کند."

    def handle(self, *args, **options):
        count = expire_stale_holds()
        self.stdout.write(self.style.SUCCESS(f"Expired booking holds released: {count}"))
