from django.core.management.base import BaseCommand
from core.utils import sync_subscription_plans

class Command(BaseCommand):
    help = 'Synchronize subscription plans with OpenStack flavors'

    def handle(self, *args, **options):
        # Call sync_subscription_plans without a request object
        success, plans = sync_subscription_plans()

        if success:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully synchronized {plans.count()} subscription plans with OpenStack.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                'Failed to sync with OpenStack. Using existing plans.'
            ))