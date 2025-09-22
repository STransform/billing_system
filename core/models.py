from django.db import models
from django.utils import timezone

from django.db import models
from accounts.models import CustomUser

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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="invoices")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=50, choices=[("pending","Pending"),("paid","Paid")])

    def __str__(self):
        return f"Invoice {self.id} - {self.project.name}"

class Payment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_id = models.CharField(max_length=255, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.project.name}"

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
    start_date  = models.DateTimeField(default=timezone.now)

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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
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
