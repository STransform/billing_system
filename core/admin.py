from django.contrib import admin
from .models import Instance, Volume, FloatingIP, Router, Snapshot, Image
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'message_preview')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'

from .models import Project, Invoice, Payment, Ticket, Notification

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_id')
    search_fields = ('name', 'project_id')
    list_filter = ('name',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'amount', 'due_date', 'status')
    search_fields = ('project__name', 'status')
    list_filter = ('status', 'due_date')
    date_hierarchy = 'due_date'
    raw_id_fields = ('project',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'project', 'amount', 'payment_date')
    search_fields = ('transaction_id', 'project__name')
    list_filter = ('payment_date',)
    date_hierarchy = 'payment_date'
    readonly_fields = ('payment_date',)
    raw_id_fields = ('project',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'project', 'status', 'created_at')
    search_fields = ('subject', 'description', 'project__name')
    list_filter = ('status', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    raw_id_fields = ('project',)
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description Preview'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'is_read', 'created_at', 'message_preview')
    search_fields = ('message', 'project__name')
    list_filter = ('is_read', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    raw_id_fields = ('project',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
    
@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ("name", "instance_id", "tenant_id", "flavor_id", "start_date")
    search_fields = ("name", "instance_id", "tenant_id")
    list_filter = ("start_date",)


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ("volume_name", "volume_id", "tenant_id", "volume_type_id", "space_allocation_gb", "start_date")
    search_fields = ("volume_name", "volume_id", "tenant_id")
    list_filter = ("start_date", "volume_type_id")


@admin.register(FloatingIP)
class FloatingIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "fip_id", "tenant_id", "start_date")
    search_fields = ("ip", "fip_id", "tenant_id")
    list_filter = ("start_date",)


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = ("name", "router_id", "tenant_id", "start_date")
    search_fields = ("name", "router_id", "tenant_id")
    list_filter = ("start_date",)


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("name", "snapshot_id", "tenant_id", "space_allocation_gb", "start_date")
    search_fields = ("name", "snapshot_id", "tenant_id")
    list_filter = ("start_date",)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("name", "image_id", "tenant_id", "space_allocation_gb", "start_date")
    search_fields = ("name", "image_id", "tenant_id")
    list_filter = ("start_date",)
