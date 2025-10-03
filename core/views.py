from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from requests import request
from django.views.generic import DetailView, View
from core.utils import sync_subscription_plans
from .forms import ContactForm, CustomerForm, PaymentForm
from openstack import connection
from openstack.exceptions import SDKException
from django.urls import reverse_lazy, reverse
from .models import FlavorPrice, Orders, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice, Instance, ContactMessage, generate_invoice_number
from .models import Invoice, SubscriptionPlan, Customer, Subscription, Cart, CartItem, Payment
from .forms import FlavorPriceForm, VolumePriceForm, IpPriceForm, RouterPriceForm, SnapShotPriceForm, ImagePriceForm
from uuid import uuid4
from datetime import timedelta
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from weasyprint import HTML 

class CustomerInvoicesView(LoginRequiredMixin, VerificationRequiredMixin, View):
    """
    Display a paginated list of customer invoices.
    """
    template_name = 'dashboard/customer/customer_invoices.html'

    def get(self, request):
        """
        Render the invoices page with paginated invoice data.
        """
        try:
            customer = Customer.objects.get(user=request.user)
            invoices = Invoice.objects.filter(customer=customer).order_by('-issue_date')

            # Paginate invoices
            paginator = Paginator(invoices, 5)
            page = request.GET.get('page')
            try:
                invoices_paginated = paginator.page(page)
            except PageNotAnInteger:
                invoices_paginated = paginator.page(1)
            except EmptyPage:
                invoices_paginated = paginator.page(paginator.num_pages)

            context = {
                'invoices': invoices_paginated,
                'invoice_count': invoices.count(),
                'model_code': 'CustomerInvoices',
            }
            return render(request, self.template_name, context)
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your invoices.")
            return redirect('core:customer_profile_create')


class CustomerProfileCreateView(LoginRequiredMixin, View):
    """
    Allow users to create a customer profile, transferring guest cart and pending subscriptions.
    """
    template_name = 'accounts/profile.html'

    def get(self, request):
        """
        Render the customer profile creation form with pre-filled user data.
        """
        if Customer.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a customer profile.")
            return redirect('core:customer_dashboard')

        # Pre-fill form with user data
        initial_data = {
            'name': f"{request.user.first_name} {request.user.last_name}".strip() or "",
            'phone': request.user.phone_number or "",
            'company': request.user.company_name or "",
            'address': request.user.address or "",
            'city': request.user.city or "",
            'state': request.user.state or "",
            'country': request.user.country or "",
            'tin_number': request.user.tin_number or "",
            'preferred_payment_method': request.user.preferred_payment_method or "",
        }

        form = CustomerForm(initial=initial_data)
        return render(request, self.template_name, {'form': form, 'model_code': 'CustomerProfile'})

    def post(self, request):
        """
        Process the customer profile creation form and handle cart/subscription transfers.
        """
        if Customer.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a customer profile.")
            return redirect('core:customer_dashboard')

        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.user = request.user
                customer.is_verified = True
                customer.tenant_id = uuid4().hex  # Generate unique tenant ID
                customer.save()
                messages.success(request, "Customer profile created successfully.")

                # Define subscription durations
                days_map = {
                    'monthly': 30,
                    'quarterly': 90,
                    'semi-annual': 180,
                    'yearly': 365
                }
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
                        messages.error(request, "Selected subscription plan no longer available.")
                    finally:
                        if 'pending_subscription' in request.session:
                            del request.session['pending_subscription']
                            request.session.modified = True

                # Convert guest cart to authenticated user
                session_key = request.session.session_key
                guest_cart = Cart.objects.filter(session_id=session_key, user__isnull=True).first()
                if guest_cart:
                    cart, created = Cart.objects.get_or_create(
                        user=request.user,
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

                # Convert cart items to pending subscriptions
                cart = Cart.objects.filter(user=request.user).first()
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
                    messages.info(request, "Your cart items have been added to your pending subscriptions.")

                return redirect('core:customer_dashboard')
            except Exception as e:
                messages.error(request, f"Error creating profile: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")

        return render(request, self.template_name, {'form': form, 'model_code': 'CustomerProfile'})


@login_required
def customer_list(request):
    """
    Display a paginated list of all customers with their latest subscriptions (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    customers = Customer.objects.all().select_related('user').prefetch_related('subscription_set__plan')
    customer_data = []
    
    for customer in customers:
        subscription = customer.subscription_set.order_by('-start_date').first()
        customer_data.append({
            'customer': customer,
            'subscription': subscription
        })

    # Paginate customer data
    paginator = Paginator(customer_data, 5)
    page = request.GET.get('page')
    try:
        customer_data_paginated = paginator.page(page)
    except PageNotAnInteger:
        customer_data_paginated = paginator.page(1)
    except EmptyPage:
        customer_data_paginated = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/admin/customer_list.html', {
        'customer_data': customer_data_paginated,
        'customer_count': len(customer_data),
        'model_code': 'Customer'
    })

