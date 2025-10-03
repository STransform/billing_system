# Import necessary Django modules for authentication, views, and utilities
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView, View
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from .forms import CustomPasswordChangeForm, CustomUserCreationForm, LoginForm, CustomUserChangeForm
from .models import CustomUser
from openstack import connection
from django.urls import reverse
from core.models import CartItem, Customer, Cart, Invoice, Subscription, SubscriptionPlan
from uuid import uuid4
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

# Initialize OpenStack connection using the 'kolla-admin' configuration
conn = connection.from_config(cloud_name="kolla-admin")


class CustomLoginView(LoginView):
    """
    Custom login view to handle user authentication, guest cart transfer, and session-based subscriptions.
    """
    form_class = LoginForm  # Custom login form
    template_name = "accounts/login.html"  # Template for login page
    redirect_authenticated_user = True  # Redirect authenticated users to avoid re-login

    def get_success_url(self):
        """
        Determine the redirect URL based on user type and verification status.
        """
        if self.request.user.is_superuser:
            return reverse_lazy('core:billing_dashboard')  # Admin users go to billing dashboard
        try:
            customer = Customer.objects.get(user=self.request.user)
            # Verified customers go to dashboard, others to profile creation
            return reverse_lazy('core:customer_dashboard') if customer.is_verified else reverse_lazy('core:customer_profile_create')
        except Customer.DoesNotExist:
            return reverse_lazy('core:customer_profile_create')  # No customer profile, redirect to create one

    
        

class CustomLogoutView(View):
    """
    View to handle user logout and session cleanup.
    """
    def get(self, request, *args, **kwargs):
        """
        Log out the user, clear the session, and redirect to login page.
        """
        logout(request)  # Log out the user
        request.session.flush()  # Clear all session data
        messages.info(request, "You have been logged out successfully.")
        return redirect(reverse_lazy("accounts:login"))  # Redirect to login page

class ProfileView(LoginRequiredMixin, DetailView):
    """
    View to display the user's profile details.
    """
    model = CustomUser  # Model for the profile
    template_name = "accounts/profile.html"  # Template for profile display
    context_object_name = "user"  # Context name for the user object

    def get_object(self, queryset=None):
        """
        Return the current user's profile.
        """
        return self.request.user

class ProfileEditView(LoginRequiredMixin, UpdateView):
    """
    View to allow users to edit their profile information.
    """
    model = CustomUser  # Model for editing
    form_class = CustomUserChangeForm  # Form for profile updates
    template_name = "accounts/profile_edit.html"  # Template for edit form
    success_url = reverse_lazy("accounts:profile")  # Redirect to profile after update

    def get_object(self, queryset=None):
        """
        Return the current user's profile for editing.
        """
        return self.request.user

class CustomPasswordChangeView(PasswordChangeView):
    """
    View to allow users to change their password.
    """
    form_class = CustomPasswordChangeForm  # Custom form for password change
    template_name = "accounts/change_password.html"  # Template for password change form
    success_url = reverse_lazy("accounts:profile")  # Redirect to profile after success

