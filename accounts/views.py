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

conn = connection.from_config(cloud_name="kolla-admin")

class RegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.save()
        customer = Customer.objects.get(user=user)
        verification_url = self.request.build_absolute_uri(
            reverse('accounts:verify_email', args=[customer.verification_token])
        )
        subject = "Verify Your Email"
        message = render_to_string('emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=message,
                fail_silently=False,
            )
            messages.success(self.request, "You have successfully registered! Please check your email to verify your account.")
        except Exception as e:
            form.add_error(None, f"Registration failed: {str(e)}")
            messages.error(self.request, f"Registration completed, but failed to send verification email: {str(e)}. Please contact support.")
            return self.form_invalid(form)
        return super().form_valid(form)

def verify_email(request, token):
    try:
        customer = Customer.objects.get(verification_token=token)
        customer.is_verified = True
        customer.verification_token = None
        customer.save()
        user = customer.user
        user.is_active = True
        user.save()
        messages.success(request, "Email verified successfully! Please log in.")
        session_key = request.session.session_key
        days_map = {
            'monthly': 30,
            'quarterly': 90,
            'semi-annual': 180,
            'yearly': 365
        }
        if session_key:
            guest_cart = Cart.objects.filter(session_id=session_key, user__isnull=True).first()
            if guest_cart:
                cart, created = Cart.objects.get_or_create(
                    user=user,
                    session_id=None,
                    defaults={'created_at': timezone.now()}
                )
                for item in guest_cart.items.all():
                    CartItem.objects.get_or_create(
                        cart=cart,
                        plan=item.plan,
                        billing_cycle=item.billing_cycle,
                        price=item.price,
                        defaults={'quantity': item.quantity}
                    )
                guest_cart.delete()
                # Convert cart to pending subscriptions
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
                cart.delete()
                messages.info(request, "Your cart items have been added to your pending subscriptions.")
        # Handle pending subscription from session
        pending_subscription = request.session.get('pending_subscription')
        if pending_subscription:
            try:
                plan = SubscriptionPlan.objects.get(id=pending_subscription['plan_id'])
                billing_cycle = pending_subscription.get('billing_cycle', 'monthly')
                if billing_cycle not in days_map:
                    billing_cycle = 'monthly'
                days = days_map[billing_cycle]
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
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse_lazy('core:billing_dashboard')
        try:
            customer = Customer.objects.get(user=self.request.user)
            return reverse_lazy('core:customer_dashboard') if customer.is_verified else reverse_lazy('core:customer_profile_create')
        except Customer.DoesNotExist:
            return reverse_lazy('core:customer_profile_create')

    def form_valid(self, form):
        user = form.get_user()
        old_session_key = self.request.session.session_key
        login(self.request, user)

        if user.is_superuser:
            return redirect(self.get_success_url())

        try:
            customer = Customer.objects.get(user=user)
            if not customer.is_verified:
                logout(self.request)
                messages.error(self.request, "Please verify your email address before logging in.")
                return redirect('accounts:login')
        except Customer.DoesNotExist:
            messages.warning(self.request, "Please create a customer profile to access your dashboard.")
            return redirect('core:customer_profile_create')

        try:
            cloud_user = conn.identity.find_user(user.username)
            if cloud_user and "default_project_id" in cloud_user:
                self.request.session["project_id"] = cloud_user["default_project_id"]
        except Exception:
            pass

        # Transfer guest cart to authenticated user
        days_map = {
            'monthly': 30,
            'quarterly': 90,
            'semi-annual': 180,
            'yearly': 365
        }
        if old_session_key:
            guest_cart = Cart.objects.filter(session_id=old_session_key, user__isnull=True).first()
            if guest_cart:
                cart, created = Cart.objects.get_or_create(
                    user=user,
                    session_id=None,
                    defaults={'created_at': timezone.now()}
                )
                for item in guest_cart.items.all():
                    CartItem.objects.get_or_create(
                        cart=cart,
                        plan=item.plan,
                        billing_cycle=item.billing_cycle,
                        price=item.price,
                        defaults={'quantity': item.quantity}
                    )
                guest_cart.delete()

        # Handle pending subscription from session
        pending_subscription = self.request.session.get('pending_subscription')
        if pending_subscription:
            try:
                plan = SubscriptionPlan.objects.get(id=pending_subscription['plan_id'])
                billing_cycle = pending_subscription.get('billing_cycle', 'monthly')
                if billing_cycle not in days_map:
                    billing_cycle = 'monthly'
                days = days_map[billing_cycle]
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
                if 'pending_subscription' in self.request.session:
                    del self.request.session['pending_subscription']
                    self.request.session.modified = True

        # Convert cart items to pending subscriptions
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
            cart.delete()
            messages.info(self.request, "Your cart items have been added to your pending subscriptions.")

        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return redirect(next_url or self.get_success_url())

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        request.session.flush()
        messages.info(request, "You have been logged out successfully.")
        return redirect(reverse_lazy("accounts:login"))

class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = "accounts/profile.html"
    context_object_name = "user"

    def get_object(self, queryset=None):
        return self.request.user

class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:profile")

@login_required
def confirm_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id, customer__user=request.user)
    if subscription.status != 'pending':
        messages.error(request, "Subscription cannot be confirmed. Only pending subscriptions can be confirmed.")
        return redirect('core:customer_subscriptions')
    try:
        subscription.status = 'active'
        subscription.start_date = timezone.now()
        duration = subscription.end_date - subscription.start_date
        subscription.end_date = subscription.start_date + duration
        subscription.save()
        invoice = Invoice.objects.create(
            customer=subscription.customer,
            subscription=subscription,
            invoice_number=f"INV-{uuid4().hex[:8]}",
            amount=subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle),
            due_date=timezone.now() + timedelta(days=30),
            issue_date=timezone.now(),
            status='pending',
            tax=Decimal('0.00'),
            total=subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle),
            subtotal_currency='ETB',
            tax_currency='ETB',
            total_currency='ETB',
        )
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
            messages.warning(request, f"Subscription confirmed, but email sending failed: {str(e)}. Please contact support.")
        return redirect('core:customer_invoices')
    except Exception as e:
        messages.error(request, f"Error confirming subscription: {str(e)}. Please contact support.")
        return redirect('core:customer_subscriptions')