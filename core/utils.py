from openstack import connection
from openstack.exceptions import SDKException
from django.contrib import messages
from decimal import Decimal
from core.models import SubscriptionPlan
from django.utils import timezone

def sync_subscription_plans(request=None):
    """
    Synchronize SubscriptionPlan objects with OpenStack flavors.
    If request is provided and supports messages, adds success/error messages.
    Returns a tuple (success: bool, plans: QuerySet).
    """
    try:
        # Connect to OpenStack
        conn = connection.from_config(cloud_name="kolla-admin")
        flavors = list(conn.compute.flavors())
        
        # Define pricing logic
        def calculate_prices(vcpus, ram, disk):
            monthly_price = (
                (vcpus * Decimal('2700')) +
                (Decimal(ram // 1024) * Decimal('2500')) +
                (Decimal(disk) * Decimal('20'))
            )
            hourly_price = monthly_price / (30 * 24)
            return hourly_price, monthly_price

        # Update or create SubscriptionPlan for each flavor
        for flavor in flavors:
            hourly_price, monthly_price = calculate_prices(flavor.vcpus, flavor.ram, flavor.disk)
            SubscriptionPlan.objects.update_or_create(
                flavor_id=flavor.id,
                defaults={
                    'name': flavor.name,
                    'vcpu': flavor.vcpus,
                    'ram': flavor.ram // 1024,
                    'os_storage': flavor.disk,
                    'data_storage': 50,
                    'hourly_price': hourly_price,
                    'monthly_price': monthly_price,
                    'quarterly_price': monthly_price * Decimal('3'),
                    'semi_annual_price': monthly_price * Decimal('6'),
                    'yearly_price': monthly_price * Decimal('12'),
                    'price_currency': 'ETB',
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                }
            )
        
        # Only add message if request is provided and supports messages
        if request and hasattr(request, 'session'):
            messages.success(request, "Subscription plans synchronized successfully with OpenStack.")
        return True, SubscriptionPlan.objects.all()
    
    except SDKException as e:
        # Only add message if request is provided and supports messages
        if request and hasattr(request, 'session'):
            messages.error(request, f"Failed to sync with OpenStack: {str(e)}. Using existing plans.")
        return False, SubscriptionPlan.objects.all()