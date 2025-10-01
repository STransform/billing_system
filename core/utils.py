
from openstack import connection
from openstack.exceptions import SDKException

from django.contrib import messages
from decimal import Decimal
from openstack import connection
from openstack.exceptions import SDKException
from django.contrib import messages
from decimal import Decimal
from core.models import SubscriptionPlan
from django.utils import timezone
# Import the SubscriptionPlan model for database operations
from core.models import SubscriptionPlan
# Import timezone utility for setting creation/update timestamps
from django.utils import timezone

def sync_subscription_plans(request=None):
    """
    Synchronize SubscriptionPlan objects with OpenStack flavors.

    This function connects to an OpenStack cloud, retrieves available flavors, calculates
    """
    try:
        # Establish connection to OpenStack using the 'kolla-admin' configuration
        conn = connection.from_config(cloud_name="kolla-admin")
        # Retrieve all available flavors from OpenStack
        flavors = list(conn.compute.flavors())
        
        # Define pricing logic based on vCPUs, RAM, and disk
        def calculate_prices(vcpus, ram, disk):
            """
            Calculate hourly and monthly prices for a flavor based on its resources.

            Args:
                vcpus (int): Number of virtual CPUs.
                ram (int): RAM in MB.
                disk (int): Disk size in GB.

            Returns:
                tuple: (hourly_price: Decimal, monthly_price: Decimal)
            """
            # To Calculate monthly price: vCPUs * 2700 + RAM (in GB) * 2500 + disk * 20
            monthly_price = (
                (vcpus * Decimal('2700')) +
                (Decimal(ram // 1024) * Decimal('2500')) +
                (Decimal(disk) * Decimal('20'))
            )
            # To Calculate hourly price: monthly price divided by hours in a month (30 days * 24 hours)
            hourly_price = monthly_price / (30 * 24)
            return hourly_price, monthly_price

        # Update or create SubscriptionPlan for each flavor
        for flavor in flavors:
            # Calculate prices for the current flavor
            hourly_price, monthly_price = calculate_prices(flavor.vcpus, flavor.ram, flavor.disk)
            # Update or create SubscriptionPlan in the database
            SubscriptionPlan.objects.update_or_create(
                flavor_id=flavor.id,  # Use flavor ID as unique identifier
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
    
        if request and hasattr(request, 'session'):
            messages.success(request, "Subscription plans synchronized successfully with OpenStack.")
        # Return success status and all SubscriptionPlan objects
        return True, SubscriptionPlan.objects.all()
    
    except SDKException as e:
        # Handle OpenStack connection or API errors
        if request and hasattr(request, 'session'):
            messages.error(request, f"Failed to sync with OpenStack: {str(e)}. Using existing plans.")
        # Return failure status and existing SubscriptionPlan objects
        return False, SubscriptionPlan.objects.all()


def sync_subscription_plans(request=None):
    """
    Synchronize SubscriptionPlan objects with OpenStack flavors.

    This function connects to an OpenStack cloud, retrieves available flavors, calculates
    pricing based on vCPUs, RAM, and disk, and updates or creates corresponding
    SubscriptionPlan objects in the database. If a request object is provided, it adds
    success or error messages to inform the user of the outcome.

    Args:
        request (HttpRequest, optional): Django request object for adding messages.
                                        Defaults to None.

    Returns:
        tuple: (success: bool, plans: QuerySet)
            - success: True if synchronization was successful, False otherwise.
            - plans: QuerySet of all SubscriptionPlan objects in the database.
    """
    try:
        # Establish connection to OpenStack using the 'kolla-admin' configuration
        conn = connection.from_config(cloud_name="kolla-admin")
        # Retrieve all available flavors from OpenStack
        flavors = list(conn.compute.flavors())
        
        # Define pricing logic based on vCPUs, RAM, and disk
        def calculate_prices(vcpus, ram, disk):
            """
            Calculate hourly and monthly prices for a flavor based on its resources.

            Args:
                vcpus (int): Number of virtual CPUs.
                ram (int): RAM in MB.
                disk (int): Disk size in GB.

            Returns:
                tuple: (hourly_price: Decimal, monthly_price: Decimal)
            """
            # Calculate monthly price: vCPUs * 2700 + RAM (in GB) * 2500 + disk * 20
            monthly_price = (
                (vcpus * Decimal('2700')) +
                (Decimal(ram // 1024) * Decimal('2500')) +
                (Decimal(disk) * Decimal('20'))
            )
            # Calculate hourly price: monthly price divided by hours in a month (30 days * 24 hours)
            hourly_price = monthly_price / (30 * 24)
            return hourly_price, monthly_price

        # Update or create SubscriptionPlan for each flavor
        for flavor in flavors:
            # Calculate prices for the current flavor
            hourly_price, monthly_price = calculate_prices(flavor.vcpus, flavor.ram, flavor.disk)
            # Update or create SubscriptionPlan in the database
            SubscriptionPlan.objects.update_or_create(
                flavor_id=flavor.id,  # Use flavor ID as unique identifier
                defaults={
                    'name': flavor.name,  # Flavor name from OpenStack
                    'vcpu': flavor.vcpus,  # Number of virtual CPUs
                    'ram': flavor.ram // 1024,  # Convert RAM from MB to GB
                    'os_storage': flavor.disk,  # Disk size in GB
                    'data_storage': 50,  # Default data storage (hardcoded to 50 GB)
                    'hourly_price': hourly_price,  # Calculated hourly price
                    'monthly_price': monthly_price,  # Calculated monthly price
                    'quarterly_price': monthly_price * Decimal('3'),  # Quarterly price (3 months)
                    'semi_annual_price': monthly_price * Decimal('6'),  # Semi-annual price (6 months)
                    'yearly_price': monthly_price * Decimal('12'),  # Yearly price (12 months)
                    'price_currency': 'ETB',  # Currency set to Ethiopian Birr
                    'created_at': timezone.now(),  # Set creation timestamp
                    'updated_at': timezone.now(),  # Set update timestamp
                }
            )
        
        # Add success message if request object is provided and supports messages
        if request and hasattr(request, 'session'):
            messages.success(request, "Subscription plans synchronized successfully with OpenStack.")
        # Return success status and all SubscriptionPlan objects
        return True, SubscriptionPlan.objects.all()
    
    except SDKException as e:
        # Handle OpenStack connection or API errors
        if request and hasattr(request, 'session'):
            messages.error(request, f"Failed to sync with OpenStack: {str(e)}. Using existing plans.")
        # Return failure status and existing SubscriptionPlan objects
        return False, SubscriptionPlan.objects.all()