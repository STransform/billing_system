from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm
@admin.register(CustomUser)
class UserAdmin(DjangoUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Company", {"fields": ("company_name", "address", "phone_number", "city", "state", "country", "tin_number", "preferred_payment_method", "operating_system")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "company_name", "address", "phone_number", "city", "state", "country", "tin_number", "preferred_payment_method", "operating_system", "password1", "password2", "is_staff", "is_active"),
        }),
    )
    list_display = ("email", "first_name", "last_name", "company_name", "is_staff")
    search_fields = ("email", "first_name", "last_name", "company_name")
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions",)