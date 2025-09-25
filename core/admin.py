from django.contrib import admin
from .models import (
    Instance, Volume, FloatingIP, Router, Snapshot, Image,
    ContactMessage, Project, Invoice, Payment, Ticket, Notification,
    Customer, Subscription, SubscriptionPlan, Cart, CartItem,
    FlavorPrice, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice
)
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'amount', 'status', 'due_date']
    list_filter = ['status', 'due_date']
    search_fields = ['invoice_number', 'customer__user__email'] # Updated to customer__user__email
    raw_id_fields = ['customer', 'subscription']
    date_hierarchy = 'due_date'
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'invoice', 'amount', 'payment_method', 'payment_date']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['transaction_id', 'invoice__invoice_number']
    raw_id_fields = ['invoice']
    readonly_fields = ['payment_date']
    date_hierarchy = 'payment_date'
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at', 'message_preview']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_id']
    search_fields = ['name', 'project_id']
    list_filter = ['name']
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'project', 'status', 'created_at']
    search_fields = ['subject', 'description', 'project__name']
    list_filter = ['status', 'created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    raw_id_fields = ['project']
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description Preview'
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'is_read', 'created_at', 'message_preview']
    search_fields = ['message', 'project__name']
    list_filter = ['is_read', 'created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    raw_id_fields = ['project']
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ['name', 'instance_id', 'tenant_id', 'flavor_id', 'start_date']
    search_fields = ['name', 'instance_id', 'tenant_id']
    list_filter = ['start_date']
@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ['volume_name', 'volume_id', 'tenant_id', 'volume_type_id', 'space_allocation_gb', 'start_date']
    search_fields = ['volume_name', 'volume_id', 'tenant_id']
    list_filter = ['start_date', 'volume_type_id']
@admin.register(FloatingIP)
class FloatingIPAdmin(admin.ModelAdmin):
    list_display = ['ip', 'fip_id', 'tenant_id', 'start_date']
    search_fields = ['ip', 'fip_id', 'tenant_id']
    list_filter = ['start_date']
@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = ['name', 'router_id', 'tenant_id', 'start_date']
    search_fields = ['name', 'router_id', 'tenant_id']
    list_filter = ['start_date']
@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ['name', 'snapshot_id', 'tenant_id', 'space_allocation_gb', 'start_date']
    search_fields = ['name', 'snapshot_id', 'tenant_id']
    list_filter = ['start_date']
@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'image_id', 'tenant_id', 'space_allocation_gb', 'start_date']
    search_fields = ['name', 'image_id', 'tenant_id']
    list_filter = ['start_date']
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'name', 'phone', 'company', 'created_at'] # Use user_email method
    search_fields = ['user__email', 'name', 'company'] # Updated to user__email
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'plan', 'status', 'start_date']
    list_filter = ['status', 'start_date']
    raw_id_fields = ['customer', 'plan']
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'vcpu', 'ram', 'monthly_price', 'price_currency']
    search_fields = ['name', 'flavor_id']
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'created_at']
    raw_id_fields = ['user']
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'plan', 'billing_cycle', 'price']
    raw_id_fields = ['cart', 'plan']
@admin.register(FlavorPrice)
class FlavorPriceAdmin(admin.ModelAdmin):
    list_display = ['flavor_id', 'hourly_price', 'monthly_price', 'price_currency']
    search_fields = ['flavor_id']
@admin.register(VolumePrice)
class VolumePriceAdmin(admin.ModelAdmin):
    list_display = ['volume_type_id', 'hourly_price', 'monthly_price', 'price_currency']
    search_fields = ['volume_type_id']
@admin.register(IpPrice)
class IpPriceAdmin(admin.ModelAdmin):
    list_display = ['hourly_price', 'monthly_price', 'price_currency']
@admin.register(RouterPrice)
class RouterPriceAdmin(admin.ModelAdmin):
    list_display = ['hourly_price', 'monthly_price', 'price_currency']
@admin.register(SnapShotPrice)
class SnapShotPriceAdmin(admin.ModelAdmin):
    list_display = ['hourly_price', 'monthly_price', 'price_currency']
@admin.register(ImagePrice)
class ImagePriceAdmin(admin.ModelAdmin):
    list_display = ['hourly_price', 'monthly_price', 'price_currency']