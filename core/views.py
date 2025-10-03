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
class VerificationRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user has a verified customer profile before accessing certain views.
    """
    def test_func(self):
        """
        Check if the user has a verified customer profile.
        Returns True if verified, False otherwise.
        """
        try:
            customer = Customer.objects.get(user=self.request.user)
            return customer.is_verified
        except Customer.DoesNotExist:
            return False

    def handle_no_permission(self):
        """
        Handle cases where the user lacks permission (unverified or no customer profile).
        Redirects to the customer profile creation page with an error message.
        """
        messages.error(self.request, "Please create or verify your customer profile to access this page.")
        return redirect('core:customer_profile_create')

def landing_page(request):
    """
    Display the landing page with subscription plans and a contact form.
    Syncs subscription plans with OpenStack and handles contact form submissions.
    """
    # Sync subscription plans with OpenStack
    result = sync_subscription_plans(request)
    if isinstance(result, tuple) and len(result) == 2:
        success, flavors = result  # Successful sync returns tuple of (success, plans)
    else:
        success = False
        flavors = result if result else SubscriptionPlan.objects.all()  # Fallback to existing plans
        messages.error(request, "Error syncing plans. Using existing plans.")
    
    # Calculate display prices for each billing cycle
    for flavor in flavors:
        flavor.monthly_price_display = flavor.monthly_price
        flavor.quarterly_price_display = flavor.get_price_for_billing_cycle('quarterly')
        flavor.semi_annual_price_display = flavor.get_price_for_billing_cycle('semi-annual')
        flavor.yearly_price_display = flavor.get_price_for_billing_cycle('yearly')

    form = ContactForm()  # Initialize contact form
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # Save contact message to database
            messages.success(request, "Your message has been sent successfully!")
            return redirect("core:landing_page")

    context = {"form": form, "flavors": flavors}
    return render(request, "landing_page/landing.html", context)

@login_required
def sync_subscription_plans_view(request):
    """
    Sync subscription plans with OpenStack (admin-only).
    Redirects to the subscription plan list after syncing.
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        # Redirect based on user role
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
    
    success, plans = sync_subscription_plans(request)  # Sync plans using utility function
    return redirect('core:subscription_plan_list')

def user_instances(request):
    """
    Retrieve instances associated with the user's tenant ID from OpenStack.
    Returns a dictionary with instance data or an error if no tenant ID is found.
    """
    tenant_id = request.session.get('project_id', None)
    if not tenant_id:
        return {
            'instances': [],
            'tenant_id': None,
            'error': 'No tenant ID found in session. Please authenticate.'
        }
    instances = Instance.objects.filter(tenant_id=tenant_id)
    return {
        'instances': instances,
        'tenant_id': tenant_id
    }

@login_required
def dashboard_redirect(request):
    """
    Redirect users to the appropriate dashboard based on their role and verification status.
    """
    if request.user.is_superuser:
        return redirect(reverse('core:billing_dashboard'))  # Admins go to billing dashboard
    else:
        try:
            customer = Customer.objects.get(user=request.user)
            # Verified customers go to customer dashboard, others to profile creation
            return redirect(reverse('core:customer_dashboard')) if customer.is_verified else redirect(reverse('core:customer_profile_create'))
        except Customer.DoesNotExist:
            return redirect(reverse('core:customer_profile_create'))  # No customer profile, redirect to create one

@login_required
@never_cache
def billing_dashboard(request):
    """
    Display the admin billing dashboard with customer, subscription, and invoice statistics.
    Accessible only to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access the admin dashboard.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    context = user_instances(request)  # Get instance data for the tenant
    # Aggregate dashboard statistics
    total_customers = Customer.objects.count()
    total_subscriptions = Subscription.objects.count()
    total_invoices = Invoice.objects.count()
    total_subscription_plans = SubscriptionPlan.objects.count()
    recent_invoices = Invoice.objects.order_by('-issue_date')[:5]
    subscriptions = Subscription.objects.select_related('customer__user', 'plan').all().order_by('-start_date')

    context.update({
        'total_customers': total_customers,
        'total_subscriptions': total_subscriptions,
        'total_invoices': total_invoices,
        'total_subscription_plans': total_subscription_plans,
        'recent_invoices': recent_invoices,
        'subscriptions': subscriptions,
        'model_code': 'BillingDashboard',
    })
    return render(request, "dashboard/admin/admin_dashboard.html", context)
class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'dashboard/admin/customer_detail_view.html'
    context_object_name = 'customer'

class CustomerDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a specific customer (admin-only).
    """
    model = Customer
    template_name = 'dashboard/admin/customer_detail_view.html'
    context_object_name = 'customer'

    def dispatch(self, request, *args, **kwargs):
        """
        Restrict access to superusers only.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """
        Retrieve the customer by ID.
        """
        return get_object_or_404(Customer, id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        """
        Add subscription data to the context for display.
        """
        context = super().get_context_data(**kwargs)
        subscription = Subscription.objects.filter(customer=self.get_object()).order_by('-start_date').first()
        context.update({
            'model_code': 'CustomerDetailView',
            'subscription': subscription,  # Latest subscription for start/end dates
        })
        return context

class AdminSubscriptionDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a specific subscription (admin-only).
    """
    model = Subscription
    template_name = 'dashboard/admin/subscription_detail.html'
    context_object_name = 'subscription'

    def dispatch(self, request, *args, **kwargs):
        """
        Restrict access to superusers only.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """
        Retrieve the subscription by ID.
        """
        return get_object_or_404(Subscription, id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        """
        Add model code to the context for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context['model_code'] = 'AdminSubscriptionDetail'
        return context

class CustomerDashboardView(LoginRequiredMixin, VerificationRequiredMixin, View):
    """
    Display the customer dashboard with subscription, invoice, and cart information.
    """
    template_name = 'dashboard/customer/customer_dashboard.html'

    def get(self, request):
        """
        Render the customer dashboard with paginated pending subscriptions and cart totals.
        """
        try:
            customer = Customer.objects.get(user=request.user)
            context = user_instances(request)  # Get instance data for the tenant

            # Aggregate dashboard statistics
            total_subscriptions = Subscription.objects.filter(customer=customer).count()
            total_invoices = Invoice.objects.filter(customer=customer).count()
            total_active_subscriptions = Subscription.objects.filter(customer=customer, status='active').count()
            recent_invoices = Invoice.objects.filter(customer=customer).order_by('-issue_date')[:5]
            pending_subscriptions = Subscription.objects.filter(customer=customer, status='pending').order_by('-start_date')

            VAT_RATE = Decimal('0.15')  # VAT rate for calculations
            pending_subscription_data = []
            for subscription in pending_subscriptions:
                base_price = subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle)
                vat_amount = base_price * VAT_RATE
                total_price = base_price + vat_amount
                pending_subscription_data.append({
                    'subscription': subscription,
                    'base_price': base_price,
                    'vat_amount': vat_amount,
                    'total_price': total_price
                })

            # Paginate pending subscriptions
            paginator = Paginator(pending_subscription_data, 5)
            page = request.GET.get('page')
            try:
                pending_subscription_data_paginated = paginator.page(page)
            except PageNotAnInteger:
                pending_subscription_data_paginated = paginator.page(1)
            except EmptyPage:
                pending_subscription_data_paginated = paginator.page(paginator.num_pages)

            # Calculate cart totals if a cart exists
            cart = Cart.objects.filter(user=request.user).first()
            total = vat = grand_total = None
            if cart and cart.items.exists():
                total, vat, grand_total = cart.calculate_total()

            context.update({
                'customer': customer,
                'total_subscriptions': total_subscriptions,
                'total_invoices': total_invoices,
                'total_active_subscriptions': total_active_subscriptions,
                'recent_invoices': recent_invoices,
                'pending_subscriptions': pending_subscription_data_paginated,
                'pending_subscription_count': len(pending_subscription_data),
                'cart': cart,
                'total': total,
                'vat': vat,
                'grand_total': grand_total,
                'model_code': 'CustomerDashboard',
            })
            return render(request, self.template_name, context)
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your dashboard.")
            return redirect('core:customer_profile_create')

class CustomerSubscriptionsView(LoginRequiredMixin, View):
    """
    Display and manage customer subscriptions with pagination and confirmation/cancellation actions.
    """
    template_name = 'dashboard/customer/customer_subscriptions.html'

    def get(self, request):
        """
        Render the subscriptions page with paginated subscription data and pricing details.
        """
        try:
            customer = Customer.objects.get(user=request.user)
            subscriptions = Subscription.objects.filter(customer=customer).select_related('plan').order_by('-start_date')

            VAT_RATE = Decimal('0.15')  # VAT rate for calculations
            subscription_data = []
            for subscription in subscriptions:
                base_price = subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle)
                vat_amount = base_price * VAT_RATE
                total_price = base_price + vat_amount
                subscription_data.append({
                    'subscription': subscription,
                    'base_price': base_price,
                    'vat_amount': vat_amount,
                    'total_price': total_price
                })

            # Paginate subscriptions
            paginator = Paginator(subscription_data, 5)
            page = request.GET.get('page')
            try:
                subscription_data_paginated = paginator.page(page)
            except PageNotAnInteger:
                subscription_data_paginated = paginator.page(1)
            except EmptyPage:
                subscription_data_paginated = paginator.page(paginator.num_pages)

            context = {
                'subscriptions': subscription_data_paginated,
                'subscription_count': len(subscription_data),
                'customer': customer,
                'model_code': 'CustomerSubscriptions',
            }
            return render(request, self.template_name, context)
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your subscriptions.")
            return redirect('core:customer_profile_create')

    def post(self, request):
        """
        Handle subscription confirmation or cancellation via POST requests.
        Supports AJAX responses for asynchronous updates.
        """
        action = request.POST.get('action')
        subscription_id = request.POST.get('subscription_id')

        if action == 'confirm' and subscription_id:
            try:
                with transaction.atomic():  # Ensure atomicity for database operations
                    subscription = Subscription.objects.get(
                        id=subscription_id,
                        customer__user=request.user,
                        status='pending'
                    )
                    subscription.status = 'confirmed'
                    subscription.save()

                    # Calculate invoice amounts
                    base_price = subscription.plan.get_price_for_billing_cycle(subscription.billing_cycle)
                    vat_amount = base_price * Decimal('0.15')
                    total_price = base_price + vat_amount
                    try:
                        # Create an invoice for the confirmed subscription
                        invoice = Invoice.objects.create(
                            customer=subscription.customer,
                            subscription=subscription,
                            invoice_number=generate_invoice_number(),
                            amount=base_price,
                            due_date=timezone.now() + timedelta(days=30),
                            issue_date=timezone.now(),
                            status='confirmed',
                            tax=vat_amount,
                            total=total_price,
                            subtotal_currency='ETB',
                            tax_currency='ETB',
                            total_currency='ETB',
                        )
                        print(f"[DEBUG] Subscription {subscription.id} status changed to 'confirmed'. Invoice {invoice.invoice_number} created with status 'confirmed'.")
                    except Exception as e:
                        print(f"[ERROR] Failed to create invoice for subscription {subscription.id}: {str(e)}")
                        messages.error(request, f"Subscription confirmed, but failed to create invoice: {str(e)}. Please contact support.")
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'subscription_id': subscription.id,
                                'status': subscription.status,
                                'message': 'Subscription confirmed, but invoice creation failed. Please contact support.'
                            })
                        return redirect('core:customer_subscriptions')

                    # Send invoice email
                    invoice_url = request.build_absolute_uri(reverse('core:invoice_detail', args=[invoice.id]))
                    subject = "New Invoice Generated"
                    message = render_to_string('emails/invoice_email.html', {
                        'user': request.user,
                        'invoice': invoice,
                        'subscription': subscription,
                        'invoice_url': invoice_url,
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
                        messages.success(request, "Subscription confirmed! Please proceed to payment.")
                    except Exception as e:
                        print(f"[DEBUG] Email sending failed: {str(e)}")
                        messages.warning(request, f"Subscription confirmed, but email sending failed: {str(e)}. Please contact support.")

                    # Handle AJAX response
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'subscription_id': subscription.id,
                            'status': subscription.status,
                            'invoice_status': invoice.status,
                            'message': 'Subscription confirmed! Please proceed to payment.'
                        })
                    return redirect('core:customer_invoices')
            except Subscription.DoesNotExist:
                print(f"[DEBUG] Subscription {subscription_id} not found or not in 'pending' status.")
                messages.error(request, "Invalid subscription or not authorized.")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid subscription or not authorized.'}, status=400)
            except Exception as e:
                print(f"[ERROR] Failed to confirm subscription {subscription_id}: {str(e)}")
                messages.error(request, f"Failed to confirm subscription: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': f'Failed to confirm subscription: {str(e)}'}, status=500)
        elif action == 'cancel' and subscription_id:
            try:
                subscription = Subscription.objects.get(
                    id=subscription_id,
                    customer__user=request.user,
                    status='pending'
                )
                subscription.delete()
                print(f"[DEBUG] Subscription {subscription_id} cancelled and deleted.")
                messages.success(request, "Pending subscription cancelled successfully.")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Subscription cancelled.'})
            except Subscription.DoesNotExist:
                print(f"[DEBUG] Subscription {subscription_id} not found for cancellation.")
                messages.error(request, "Subscription not found.")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Subscription not found.'}, status=400)

        return redirect('core:customer_subscriptions')

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

@login_required
def invoice_detail(request, pk):
    """
    Display detailed information about a specific invoice, including associated payments.
    """
    invoice = get_object_or_404(Invoice, id=pk)
    # Restrict access to superusers or the invoice's owner
    if not request.user.is_superuser and invoice.customer.user != request.user:
        messages.error(request, "You do not have permission to view this invoice.")
        return redirect('core:customer_invoices') if request.user.is_authenticated else redirect('core:landing_page')

    payments = Payment.objects.filter(invoice=invoice)
    context = {
        'invoice': invoice,
        'payments': payments,
        'model_code': 'InvoiceDetail',
    }
    return render(request, 'dashboard/admin/invoice_detail.html', context)

class CustomerProfileCreateView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        """
        Render the customer profile creation form with pre-filled user data.
        """
        if Customer.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a customer profile.")
            return redirect('core:customer_dashboard')

        # Pre-fill form with fields available in CustomUser
        initial_data = {
            'name': f"{request.user.first_name} {request.user.last_name}".strip() or "",
            'phone': request.user.phone_number or "",
            'company': request.user.company_name or "",
            'address': request.user.address or "",
            'tin_number': request.user.vat_number or "",  # Map vat_number to tin_number
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

class PaymentView(LoginRequiredMixin, View):
    """
    Handle payment processing for invoices and update subscription status.
    """
    template_name = 'dashboard/customer/payment.html'

    def get(self, request, invoice_id):
        """
        Render the payment form for a specific invoice.
        """
        invoice = get_object_or_404(Invoice, id=invoice_id, customer__user=request.user)
        form = PaymentForm(initial={'invoice': invoice, 'amount': invoice.total})
        context = {
            'form': form,
            'invoice': invoice,
            'model_code': 'Payment'
        }
        return render(request, self.template_name, context)

    def post(self, request, invoice_id):
        """
        Process payment form submission, create payment record, and send confirmation email.
        """
        invoice = get_object_or_404(Invoice, id=invoice_id, customer__user=request.user)
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():  # Ensure atomicity for database operations
                    payment = Payment(
                        invoice=invoice,
                        amount=form.cleaned_data['amount'],
                        payment_method=form.cleaned_data['payment_method'],
                        transaction_id=form.cleaned_data['reference_number'] or None,
                        reference_number=form.cleaned_data['reference_number'] or None
                    )
                    payment.save()

                    # Update invoice status based on total payments
                    total_paid = Payment.objects.filter(invoice=invoice).aggregate(total=models.Sum('amount'))['total'] or 0
                    if total_paid >= invoice.total:
                        invoice.status = 'paid'
                        invoice.save()

                        # Activate subscription if applicable
                        if invoice.subscription and invoice.subscription.status in ['pending', 'confirmed']:
                            subscription = invoice.subscription
                            subscription.status = 'active'
                            subscription.start_date = timezone.now()
                            days_map = {
                                'monthly': 30,
                                'quarterly': 90,
                                'semi-annual': 180,
                                'yearly': 365
                            }
                            subscription.end_date = timezone.now() + timedelta(days=days_map.get(subscription.billing_cycle, 30))
                            subscription.save()

                            # Send subscription activation email
                            dashboard_url = request.build_absolute_uri(reverse('core:customer_dashboard'))
                            subject = "Subscription Activated"
                            message = render_to_string('emails/subscription_email.html', {
                                'user': request.user,
                                'subscription': subscription,
                                'dashboard_url': dashboard_url,
                            })
                            send_mail(
                                subject,
                                message,
                                settings.DEFAULT_FROM_EMAIL,
                                [invoice.customer.user.email],
                                html_message=message,
                                fail_silently=False,
                            )

                    # Send payment confirmation email
                    invoices_url = request.build_absolute_uri(reverse('core:customer_invoices'))
                    subject = "Payment Confirmation"
                    message = render_to_string('emails/payment_email.html', {
                        'user': request.user,
                        'invoice': invoice,
                        'payment': payment,
                        'invoices_url': invoices_url,
                    })
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [invoice.customer.user.email],
                        html_message=message,
                        fail_silently=False,
                    )

                    messages.success(request, "Payment submitted successfully. Awaiting confirmation.")
                    return redirect('core:customer_dashboard')
            except Exception as e:
                messages.error(request, f"Error processing payment: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")

        context = {
            'form': form,
            'invoice': invoice,
            'model_code': 'Payment'
        }
        return render(request, self.template_name, context)

def add_to_cart(request, plan_id=None):
    """
    Add a subscription plan to the user's cart (supports both authenticated and guest users).
    """
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id', plan_id)
        billing_cycle = request.POST.get('billing_cycle', 'monthly')

    if not plan_id:
        messages.error(request, "No plan selected.")
        return redirect('core:landing_page')

    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # Validate billing cycle
    valid_billing_cycles = ['monthly', 'quarterly', 'semi-annual', 'yearly']
    if billing_cycle not in valid_billing_cycles:
        billing_cycle = 'monthly'

    price = plan.get_price_for_billing_cycle(billing_cycle)  # Get price for the selected cycle

    # Create or get cart for authenticated or guest user
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            session_id=None,
            defaults={'created_at': timezone.now()}
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(
            session_id=session_key,
            user=None,
            defaults={'created_at': timezone.now()}
        )
        # Store subscription details in session for guest users
        request.session['pending_subscription'] = {
            'plan_id': plan_id,
            'billing_cycle': billing_cycle,
            'price': str(price)
        }

    # Add item to cart
    CartItem.objects.create(
        cart=cart,
        plan=plan,
        billing_cycle=billing_cycle,
        price=price
    )

    # Notify user based on authentication status
    if request.user.is_authenticated:
        messages.success(request, f"{plan.name} ({billing_cycle.capitalize()}) added to cart!")
    else:
        messages.info(request, f"{plan.name} ({billing_cycle.capitalize()}) added to cart! Please login to checkout.")

    return redirect('core:cart_view')

def remove_from_cart(request, item_id):
    """
    Remove a specific item from the user's cart.
    """
    if request.user.is_authenticated:
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        item = get_object_or_404(CartItem, id=item_id, cart__session_id=request.session.session_key)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('core:cart_view')

def cart_view(request):
    """
    Display the user's cart with total calculations and handle checkout initiation.
    """
    # Get or create cart based on authentication status
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_id=session_key).first()

    if cart:
        total, vat, grand_total = cart.calculate_total()
        context = {
            'cart': cart,
            'total': total,
            'vat': vat,
            'grand_total': grand_total,
            'model_code': 'CartView'
        }
    else:
        context = {'cart': None, 'model_code': 'CartView'}

    # Handle checkout action
    if request.method == 'POST' and request.POST.get('action') == 'proceed_to_checkout':
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to proceed to checkout.")
            return redirect('accounts:login')
        elif not Customer.objects.filter(user=request.user).exists():
            messages.warning(request, "Please create a customer profile to proceed.")
            return redirect('core:customer_profile_create')
        else:
            if cart and cart.items.exists():
                request.session['checkout_cart'] = [
                    {
                        'plan_id': item.plan.id,
                        'billing_cycle': item.billing_cycle,
                        'price': str(item.price)
                    } for item in cart.items.all()
                ]
            return redirect('core:customer_dashboard')

    return render(request, 'cart.html', context)

@login_required
def checkout(request):
    """
    Handle the checkout process by transferring cart items to pending subscriptions.
    """
    try:
        customer = Customer.objects.get(user=request.user)
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_id=session_key, user__isnull=True).first()
            if cart:
                cart.user = request.user
                cart.session_id = None
                cart.save()

        if not cart or not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('core:cart_view')

        messages.info(request, "Please confirm your order in the dashboard.")
        return redirect('core:customer_dashboard')
    except Customer.DoesNotExist:
        messages.warning(request, "Please create a customer profile to proceed.")
        return redirect('core:customer_profile_create')

class PricingView(LoginRequiredMixin, View):
    """
    Display pricing configurations for various resources (admin-only).
    """
    def get(self, request, *args, **kwargs):
        """
        Render the pricing configuration page with all price models.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

        context = {
            'flavor_prices': FlavorPrice.objects.all(),
            'volume_prices': VolumePrice.objects.all(),
            'ip_prices': IpPrice.objects.all(),
            'router_prices': RouterPrice.objects.all(),
            'snapshot_prices': SnapShotPrice.objects.all(),
            'image_prices': ImagePrice.objects.all(),
            'model_code': 'PriceConfiguration',
        }
        return render(request, 'dashboard/price_configuration/price_conf.html', context)

class DynamicPriceCreateView(LoginRequiredMixin, View):
    """
    Create a new price entry for a specific resource type (admin-only).
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Restrict access to superusers only.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, model_name):
        """
        Render the price creation form for the specified model.
        """
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.error(request, "Invalid model name.")
            return redirect('core:price_configuration')

        form = model_info['form']()
        return render(request, 'dashboard/price_configuration/price_form.html', {
            'form': form,
            'model_name': model_name,
            'model_code': 'PriceCreate'
        })

    def post(self, request, model_name):
        """
        Process the price creation form and save the new price entry.
        """
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.error(request, "Invalid model name.")
            return redirect('core:price_configuration')

        form = model_info['form'](request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{model_name.capitalize()} price created successfully.")
            return redirect('core:price_configuration')
        return render(request, 'dashboard/price_configuration/price_form.html', {
            'form': form,
            'model_name': model_name,
            'model_code': 'PriceCreate'
        })

class DynamicPriceUpdateView(LoginRequiredMixin, View):
    """
    Update an existing price entry for a specific resource type (admin-only).
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Restrict access to superusers only.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, model_name, pk):
        """
        Render the price update form for the specified price entry.
        """
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.error(request, "Invalid model name.")
            return redirect('core:price_configuration')

        instance = get_object_or_404(model_info['model'], pk=pk)
        form = model_info['form'](instance=instance)
        return render(request, 'dashboard/price_configuration/price_form.html', {
            'form': form,
            'model_name': model_name,
            'model_code': 'PriceUpdate'
        })

    def post(self, request, model_name, pk):
        """
        Process the price update form and save changes.
        """
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.error(request, "Invalid model name.")
            return redirect('core:price_configuration')

        instance = get_object_or_404(model_info['model'], pk=pk)
        form = model_info['form'](request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{model_name.capitalize()} price updated successfully.")
            return redirect('core:price_configuration')
        return render(request, 'dashboard/price_configuration/price_form.html', {
            'form': form,
            'model_name': model_name,
            'model_code': 'PriceUpdate'
        })

class DynamicPriceDeleteView(LoginRequiredMixin, View):
    """
    Delete a price entry for a specific resource type (admin-only).
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Restrict access to superusers only.
        """
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, model_name, pk):
        """
        Delete the specified price entry.
        """
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.error(request, "Invalid model name.")
            return redirect('core:price_configuration')

        instance = get_object_or_404(model_info['model'], pk=pk)
        instance.delete()
        messages.success(request, f"{model_name.capitalize()} price deleted successfully.")
        return redirect('core:price_configuration')

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

@login_required
def customer_detail(request, customer_id):
    """
    Display detailed information about a specific customer and their latest subscription (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    customer = get_object_or_404(Customer, id=customer_id)
    subscription = Subscription.objects.filter(customer=customer).order_by('-start_date', '-created_at').first()

    if not subscription:
        messages.info(request, "No subscriptions found for this customer.")

    context = {
        'customer': customer,
        'subscription': subscription,
        'model_code': 'CustomerDetail',
    }
    return render(request, 'dashboard/admin/customer_detail.html', context)

@login_required
def invoice_list(request):
    """
    Display a paginated list of all invoices (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    invoices = Invoice.objects.all().order_by('-issue_date')
    paginator = Paginator(invoices, 5)
    page = request.GET.get('page')
    try:
        invoices_paginated = paginator.page(page)
    except PageNotAnInteger:
        invoices_paginated = paginator.page(1)
    except EmptyPage:
        invoices_paginated = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/admin/invoice_list.html', {
        'invoices': invoices_paginated,
        'model_code': 'Invoice'
    })

@login_required
def subscription_plan_list(request):
    """
    Display a paginated list of all subscription plans (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    plans = SubscriptionPlan.objects.all()
    plan_count = plans.count()

    # Paginate plans
    paginator = Paginator(plans, 5)
    page = request.GET.get('page')
    try:
        plans_paginated = paginator.page(page)
    except PageNotAnInteger:
        plans_paginated = paginator.page(1)
    except EmptyPage:
        plans_paginated = paginator.page(paginator.num_pages)

    if plan_count == 0:
        messages.info(request, "No subscription plans found. Try syncing with OpenStack.")

    return render(request, 'dashboard/admin/subscription_plan_list.html', {
        'plans': plans_paginated,
        'plan_count': plan_count,
        'model_code': 'SubscriptionPlan'
    })

@login_required
def subscription_list(request):
    """
    Display a paginated list of all subscriptions (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    subscriptions = Subscription.objects.select_related('customer__user', 'plan').all().order_by('-start_date')
    subscription_count = subscriptions.count()

    # Paginate subscriptions
    paginator = Paginator(subscriptions, 5)
    page = request.GET.get('page')
    try:
        subscriptions_paginated = paginator.page(page)
    except PageNotAnInteger:
        subscriptions_paginated = paginator.page(1)
    except EmptyPage:
        subscriptions_paginated = paginator.page(paginator.num_pages)

    if subscription_count == 0:
        messages.info(request, "No subscriptions found. Customers may not have confirmed any subscriptions yet.")

    context = {
        'subscriptions': subscriptions_paginated,
        'subscription_count': subscription_count,
        'model_code': 'Subscription'
    }
    return render(request, 'dashboard/admin/subscription_list.html', context)

@login_required
def contact_submission_list(request):
    """
    Display a list of contact form submissions (admin-only).
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    submissions = ContactMessage.objects.all()
    return render(request, 'dashboard/contact_submission_list.html', {
        'submissions': submissions,
        'model_code': 'ContactSubmission'
    })

MODEL_MAP = {
    'flavor': {'model': FlavorPrice, 'form': FlavorPriceForm, 'id_field': 'flavor_id'},
    'volume': {'model': VolumePrice, 'form': VolumePriceForm, 'id_field': 'volume_type_id'},
    'ip': {'model': IpPrice, 'form': IpPriceForm, 'id_field': 'id'},
    'router': {'model': RouterPrice, 'form': RouterPriceForm, 'id_field': 'id'},
    'snapshot': {'model': SnapShotPrice, 'form': SnapShotPriceForm, 'id_field': 'id'},
    'image': {'model': ImagePrice, 'form': ImagePriceForm, 'id_field': 'id'},
}
@login_required
def download_invoice_pdf(request, pk):
    """
    Generate and download a PDF version of the specified invoice.
    Accessible to superusers or the invoice's owner.
    """
    invoice = get_object_or_404(Invoice, id=pk)
    # Restrict access to superusers or the invoice's owner
    if not request.user.is_superuser and invoice.customer.user != request.user:
        messages.error(request, "You do not have permission to view this invoice.")
        return redirect('core:customer_invoices') if request.user.is_authenticated else redirect('core:landing_page')

    # Render the PDF template with invoice data
    logo_url = request.build_absolute_uri('/static/img/logo.png')  
    html_string = render_to_string('dashboard/customer/invoice_pdf.html', {
        'invoice': invoice,
        'logo_url': logo_url,
    })

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    HTML(string=html_string).write_pdf(response)

    return response