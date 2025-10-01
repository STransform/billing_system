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

class RegisterView(CreateView):
    """
    View for handling user registration. Creates a new user and sends a verification email.
    """
    model = CustomUser  # The model to create (custom user model)
    form_class = CustomUserCreationForm  # Form for user registration
    template_name = "accounts/register.html"  # Template for the registration page
    success_url = reverse_lazy("accounts:login")  # URL to redirect to after successful registration

    def get_form_kwargs(self):
        """
        Pass the request object to the form to allow custom validation or processing.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Handle valid form submission: save user, create customer, and send verification email.
        """
        user = form.save()  # Save the new user
        customer = Customer.objects.get(user=user)  # Get the associated customer (assumed to be created automatically)
        # Build the email verification URL with the customer's verification token
        verification_url = self.request.build_absolute_uri(
            reverse('accounts:verify_email', args=[customer.verification_token])
        )
        subject = "Verify Your Email"  # Email subject
        # Render the email template with user and verification URL
        message = render_to_string('emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        try:
            # Send the verification email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=message,
                fail_silently=False,
            )
            # Notify user of successful registration
            messages.success(self.request, "You have successfully registered! Please check your email to verify your account.")
        except Exception as e:
            # Handle email sending failure
            form.add_error(None, f"Registration failed: {str(e)}")
            messages.error(self.request, f"Registration completed, but failed to send verification email: {str(e)}. Please contact support.")
            return self.form_invalid(form)  # Return form with error
        return super().form_valid(form)  # Proceed with form validation

def verify_email(request, token):
    """
    Verify a user's email using a token. Activates the user account and transfers any guest cart or pending subscriptions.
    """
    try:
        # Find the customer with the provided verification token
        customer = Customer.objects.get(verification_token=token)
        customer.is_verified = True  # Mark customer as verified
        customer.verification_token = None  # Clear the verification token
        customer.save()
        user = customer.user
        user.is_active = True  # Activate the user account
        user.save()
        messages.success(request, "Email verified successfully! Please log in.")

        # Define subscription durations for different billing cycles
        days_map = {
            'monthly': 30,
            'quarterly': 90,
            'semi-annual': 180,
            'yearly': 365
        }

        # Transfer guest cart to authenticated user if it exists
        session_key = request.session.session_key
        if session_key:
            guest_cart = Cart.objects.filter(session_id=session_key, user__isnull=True).first()
            if guest_cart:
                # Create or get a cart for the authenticated user
                cart, created = Cart.objects.get_or_create(
                    user=user,
                    session_id=None,
                    defaults={'created_at': timezone.now()}
                )
                # Transfer cart items from guest cart to user cart
                for item in guest_cart.items.all():
                    CartItem.objects.get_or_create(
                        cart=cart,
                        plan=item.plan,
                        billing_cycle=item.billing_cycle,
                        price=item.price,
                        defaults={'quantity': item.quantity}
                    )
                guest_cart.delete()  # Delete the guest cart
                # Convert cart items to pending subscriptions
                for item in cart.items.all():
                    days = days_map.get(item.billing_cycle, 30)
                    Subscription.objects.get_or_create(
                        customer=customer,
                        plan=item.plan,
                        billing_cycle=item.billing_cycle,
                        status='pending',
                        defaults={
                            'start_date': timezone.now(),
                            'end_date': timezone.now() + timedelta(days=days)
                        }
                    )
                cart.delete()  # Delete the cart after converting to subscriptions
                messages.info(request, "Your cart items have been added to your pending subscriptions.")

        # Handle pending subscription stored in session
        pending_subscription = request.session.get('pending_subscription')
        if pending_subscription:
            try:
                # Retrieve the subscription plan from the session
                plan = SubscriptionPlan.objects.get(id=pending_subscription['plan_id'])
                billing_cycle = pending_subscription.get('billing_cycle', 'monthly')
                if billing_cycle not in days_map:
                    billing_cycle = 'monthly'  # Default to monthly if invalid
                days = days_map[billing_cycle]
                # Create a pending subscription for the customer
                Subscription.objects.get_or_create(
                    customer=customer,
                    plan=plan,
                    billing_cycle=billing_cycle,
                    status='pending',
                    defaults={
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=days)
                    }
                )
                messages.info(request, f"{plan.name} ({billing_cycle.capitalize()}) has been added to your pending subscriptions.")
            except SubscriptionPlan.DoesNotExist:
                messages.error(request, "Selected subscription plan is no longer available.")
            finally:
                if 'pending_subscription' in request.session:
                    del request.session['pending_subscription']
                    request.session.modified = True
    except Customer.DoesNotExist:
        messages.error(request, "Invalid verification token.")
    return redirect('accounts:login')

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

    def form_valid(self, form):
        """
        Handle valid login form: authenticate user, transfer guest cart, and handle pending subscriptions.
        """
        user = form.get_user()
        old_session_key = self.request.session.session_key
        login(self.request, user)  # Log in the user

        if user.is_superuser:
            return redirect(self.get_success_url())  # Admins skip further checks

        try:
            customer = Customer.objects.get(user=user)
            if not customer.is_verified:
                logout(self.request)  # Log out unverified users
                messages.error(self.request, "Please verify your email address before logging in.")
                return redirect('accounts:login')
        except Customer.DoesNotExist:
            messages.warning(self.request, "Please create a customer profile to access your dashboard.")
            return redirect('core:customer_profile_create')

        # Check OpenStack for user's project ID and store in session
        try:
            cloud_user = conn.identity.find_user(user.username)
            if cloud_user and "default_project_id" in cloud_user:
                self.request.session["project_id"] = cloud_user["default_project_id"]
        except Exception:
            pass  # Silently ignore OpenStack errors

        # Define subscription durations
        days_map = {
            'monthly': 30,
            'quarterly': 90,
            'semi-annual': 180,
            'yearly': 365
        }

        # Transfer guest cart to authenticated user
        if old_session_key:
            guest_cart = Cart.objects.filter(session_id=old_session_key, user__isnull=True).first()
            if guest_cart:
                cart, created = Cart.objects.get_or_create(
                    user=user,
                    session_id=None,
                    defaults={'created_at': timezone.now()}
                )
                # Copy guest cart items to user cart
                for item in guest_cart.items.all():
                    CartItem.objects.get_or_create(
                        cart=cart,
                        plan=item.plan,
                        billing_cycle=item.billing_cycle,
                        price=item.price,
                        defaults={'quantity': item.quantity}
                    )
                guest_cart.delete()  # Delete the guest cart

        # Handle pending subscription from session
        pending_subscription = self.request.session.get('pending_subscription')
        if pending_subscription:
            try:
                plan = SubscriptionPlan.objects.get(id=pending_subscription['plan_id'])
                billing_cycle = pending_subscription.get('billing_cycle', 'monthly')
                if billing_cycle not in days_map:
                    billing_cycle = 'monthly'  # Default to monthly if invalid
                days = days_map[billing_cycle]
                # Create a pending subscription
                Subscription.objects.get_or_create(
                    customer=customer,
                    plan=plan,
                    billing_cycle=billing_cycle,
                    status='pending',
                    defaults={
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=days)
                    }
                )
                messages.info(self.request, f"{plan.name} ({billing_cycle.capitalize()}) has been added to your pending subscriptions.")
            except SubscriptionPlan.DoesNotExist:
                messages.error(self.request, "Selected subscription plan is no longer available.")
            finally:
                # Clear pending subscription from session
                if 'pending_subscription' in self.request.session:
                    del self.request.session['pending_subscription']
                    self.request.session.modified = True

        # Convert user cart items to pending subscriptions
        cart = Cart.objects.filter(user=user).first()
        if cart and cart.items.exists():
            for item in cart.items.all():
                days = days_map.get(item.billing_cycle, 30)
                Subscription.objects.get_or_create(
                    customer=customer,
                    plan=item.plan,
                    billing_cycle=item.billing_cycle,
                    status='pending',
                    defaults={
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=days)
                    }
                )
            cart.delete()  # Delete the cart after conversion
            messages.info(self.request, "Your cart items have been added to your pending subscriptions.")

        # Redirect to next URL if provided, otherwise to success URL
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return redirect(next_url or self.get_success_url())

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

@login_required
def confirm_subscription(request, subscription_id):
    """
    Confirm a pending subscription, create an invoice, and send a confirmation email.
    Only accessible to authenticated users for their own subscriptions.
    """
    # Retrieve the subscription, ensuring it belongs to the current user
    subscription = get_object_or_404(Subscription, id=subscription_id, customer__user=request.user)
    
    # Check if the subscription is pending
    if subscription.status != 'pending':
        messages.error(request, "Subscription cannot be confirmed. Only pending subscriptions can be confirmed.")
        return redirect('core:customer_subscriptions')
    
    try:
        # Update subscription to active status
        subscription.status = 'active'
        subscription.start_date = timezone.now()
        duration = subscription.end_date - subscription.start_date
        subscription.end_date = subscription.start_date + duration  # Maintain original duration
        subscription.save()
        
        # Create an invoice for the subscription
        invoice = Invoice.objects.create(
            customer=subscription.customer,
            subscription=subscription,
            invoice_number=f"INV-{uuid4().hex[:8]}",  # Generate unique invoice number
            amount=subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle),
            due_date=timezone.now() + timedelta(days=30),
            issue_date=timezone.now(),
            status='pending',
            tax=Decimal('0.00'),  # Tax is currently set to 0
            total=subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle),
            subtotal_currency='ETB',
            tax_currency='ETB',
            total_currency='ETB',
        )
        
        # Prepare and send confirmation email
        dashboard_url = request.build_absolute_uri(reverse('core:customer_dashboard'))
        subject = "Subscription Confirmation"
        message = render_to_string('emails/subscription_email.html', {
            'user': request.user,
            'subscription': subscription,
            'invoice': invoice,
            'dashboard_url': dashboard_url,
        })
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [subscription.customer.user.email],
                html_message=message,
                fail_silently=False,
            )
            messages.success(request, "Subscription confirmed successfully! Please proceed to payment.")
        except Exception as e:
            # Warn user if email sending fails
            messages.warning(request, f"Subscription confirmed, but email sending failed: {str(e)}. Please contact support.")
        
        return redirect('core:customer_invoices')  # Redirect to invoices page
    except Exception as e:
        # Handle any errors during confirmation
        messages.error(request, f"Error confirming subscription: {str(e)}. Please contact support.")
        return redirect('core:customer_subscriptions')