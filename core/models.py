from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.conf import settings
import uuid
from decimal import Decimal
# callable for generating invoice numbers
def generate_invoice_number():
    """
    Generate an invoice number in the format INV-<sequential_number>-MMDDYYYY.
    The sequential number increments daily, starting from 1.
    """
    today = timezone.now().date()
    date_str = today.strftime('%m%d%Y')  # Format as MMDDYYYY, e.g., 09252025
    prefix = 'INV-'
    suffix = f'-{date_str}'
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Lock invoices for today to prevent concurrent updates
                last_invoice = Invoice.objects.filter(
                    invoice_number__startswith=prefix,
                    invoice_number__endswith=suffix
                ).order_by('-invoice_number').select_for_update().first()
                
                seq_number = 1
                if last_invoice:
                    try:
                        # Extract the sequential number (e.g., INV-5-09252025 -> 5)
                        seq_number = int(last_invoice.invoice_number.split('-')[1]) + 1
                    except (IndexError, ValueError):
                        seq_number = 1  # Fallback to 1 if parsing fails
                
                invoice_number = f'{prefix}{seq_number}{suffix}'
                
                # Verify uniqueness before returning
                if not Invoice.objects.filter(invoice_number=invoice_number).exists():
                    return invoice_number
        except IntegrityError:
            if attempt == max_retries - 1:
                raise ValueError("Unable to generate unique invoice number after retries.")
            continue  # Retry on IntegrityError
    raise ValueError("Unable to generate unique invoice number after retries.")

class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.name} ({self.email})"
class Project(models.Model):
    project_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    def __str__(self):
        return f"{self.name} ({self.project_id})"
class Invoice(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE, null=True)
    invoice_number = models.CharField(max_length=50, unique=True, default=generate_invoice_number)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issue_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('overdue', 'Overdue')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal_currency = models.CharField(max_length=3, default='ETB')
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    tax_currency = models.CharField(max_length=3, default='ETB')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_currency = models.CharField(max_length=3, default='ETB')
    state = models.CharField(max_length=20, default='draft')

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    class Meta:
        ordering = ['-issue_date']
# Rest of the models remain unchanged
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[('bank_transfer', 'Bank Transfer'), ('telebirr', 'Telebirr')]
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Payment {self.transaction_id} for Invoice {self.invoice.invoice_number}"
class Ticket(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tickets")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=[("open","Open"),("closed","Closed")], default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Ticket {self.id} - {self.subject}"
class Notification(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    def __str__(self):
        return f"Notification {self.id} - {self.project.name}"
class Instance(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    instance_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    flavor_id = models.CharField(max_length=128)
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.name} ({self.instance_id})"
class Volume(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    volume_id = models.CharField(max_length=128, unique=True)
    volume_name = models.CharField(max_length=255)
    volume_type_id = models.CharField(max_length=128, blank=True, null=True)
    space_allocation_gb = models.IntegerField()
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.volume_name} ({self.volume_id})"
class FloatingIP(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    fip_id = models.CharField(max_length=128, unique=True)
    ip = models.GenericIPAddressField()
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.ip} ({self.fip_id})"
class Router(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    router_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.name} ({self.router_id})"
class Snapshot(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    snapshot_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    space_allocation_gb = models.IntegerField()
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.name} ({self.snapshot_id})"
class Image(models.Model):
    tenant_id = models.CharField(max_length=128, db_index=True)
    image_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    space_allocation_gb = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    start_date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.name} ({self.image_id})"
class FlavorPrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    flavor_id = models.CharField(max_length=256)
class VolumePrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    volume_type_id = models.CharField(max_length=256)
class IpPrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
class RouterPrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
class SnapShotPrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
class ImagePrice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
class Orders(models.Model):
    BILLING_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi-annual", "Semi-Annual"),
        ("yearly", "Yearly"),
    ]
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    flavor_name = models.CharField(max_length=50)
    billing_cycle = models.CharField(max_length=50, choices=BILLING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    vcpu = models.IntegerField()
    ram = models.IntegerField()
    os_storage = models.IntegerField(default=30)
    data_storage = models.IntegerField()
    add_volume = models.IntegerField(default=0)
    os = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255)
    vcpu = models.IntegerField()
    ram = models.IntegerField()
    os_storage = models.IntegerField(default=30)
    data_storage = models.IntegerField(default=50)
    hourly_price = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10, default='ETB')
    flavor_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
class Cart(models.Model):
    session_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def calculate_total(self):
        total = sum(item.subtotal() for item in self.items.all())
        vat = total * Decimal('0.15')
        return total, vat, total + vat
    def __str__(self):
        return f"Cart {self.id} for {self.user or 'Guest'}"
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    billing_cycle = models.CharField(
        max_length=50,
        choices=[("monthly", "Monthly"), ("quarterly", "Quarterly"), ("semi-annual", "Semi-Annual"), ("yearly", "Yearly")],
        default="monthly"
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    def subtotal(self):
        return self.price * self.quantity
    def __str__(self):
        return f"{self.quantity} x {self.plan.name} ({self.billing_cycle})"
class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    tin_number = models.CharField(max_length=100, blank=True, null=True)
    preferred_payment_method = models.CharField(
        max_length=50,
        choices=[
            ('bank_transfer', 'Bank Transfer'),
            ('telebirr', 'Telebirr'),
        ],
        blank=True,
        null=True
    )
    operating_system = models.CharField(
        max_length=50,
        choices=[
            ('ubuntu_22_04_server', 'Ubuntu 22.04 Server'),
            ('ubuntu_24_04_server', 'Ubuntu 24.04 Server'),
            ('ubuntu_22_04_desktop', 'Ubuntu 22.04 Desktop'),
            ('ubuntu_24_04_desktop', 'Ubuntu 24.04 Desktop'),
            ('windows_server_2019', 'Windows Server 2019'),
            ('windows_desktop', 'Windows Desktop'),
        ],
        blank=True,
        null=True
    )
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    tenant_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name or self.user.email if self.user else "Unnamed Customer"
class Subscription(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('active', 'Active'), ('cancelled', 'Cancelled'), ('expired', 'Expired')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.plan.name} for {self.customer}"