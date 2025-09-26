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
from .forms import ContactForm, CustomerForm
from openstack import connection
from openstack.exceptions import SDKException
from django.views.generic import View
from django.urls import reverse_lazy, reverse
from .models import FlavorPrice, Orders, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice, Instance, ContactMessage
from .models import Invoice, SubscriptionPlan, Customer, Subscription, Cart, CartItem, Payment
from .forms import FlavorPriceForm, VolumePriceForm, IpPriceForm, RouterPriceForm, SnapShotPriceForm, ImagePriceForm
from uuid import uuid4
from datetime import timedelta
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class VerificationRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        try:
            customer = Customer.objects.get(user=self.request.user)
            return customer.is_verified
        except Customer.DoesNotExist:
            return False

    def handle_no_permission(self):
        messages.error(self.request, "Please create or verify your customer profile to access this page.")
        return redirect('core:customer_profile_create')

def landing_page(request):
    flavors = []
    try:
        conn = connection.from_config(cloud_name="kolla-admin")
        openstack_flavors = list(conn.compute.flavors())
        for os_flavor in openstack_flavors:
            flavor_price = FlavorPrice.objects.filter(flavor_id=os_flavor.id).first()
            SubscriptionPlan.objects.update_or_create(
                flavor_id=os_flavor.id,
                defaults={
                    'name': os_flavor.name,
                    'vcpu': os_flavor.vcpus,
                    'ram': os_flavor.ram // 1024,
                    'os_storage': 30,
                    'data_storage': 50,
                    'hourly_price': flavor_price.hourly_price if flavor_price else Decimal('0.10'),
                    'monthly_price': flavor_price.monthly_price if flavor_price else (
                        (os_flavor.vcpus * Decimal('2700')) +
                        (Decimal(os_flavor.ram // 1024) * Decimal('2500')) +
                        (Decimal('30') * Decimal('20')) +
                        (Decimal('50') * Decimal('20'))
                    ),
                    'price_currency': flavor_price.price_currency if flavor_price else 'ETB',
                }
            )
        flavors = SubscriptionPlan.objects.all()
    except SDKException:
        messages.warning(request, "OpenStack connection failed. Using fallback data. Contact OTech for API access.")
        hardcoded_flavors = [
            {"name": "OSTD.1-2", "vcpu": 1, "ram": 2, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.10'), "monthly_price": Decimal('6700'), "price_currency": "ETB", "flavor_id": "ostd.1-2"},
            {"name": "OSTD.2-4", "vcpu": 2, "ram": 4, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.20'), "monthly_price": Decimal('11900'), "price_currency": "ETB", "flavor_id": "ostd.2-4"},
            {"name": "OSTD.2-8", "vcpu": 2, "ram": 8, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.30'), "monthly_price": Decimal('17100'), "price_currency": "ETB", "flavor_id": "ostd.2-8"},
            {"name": "OSTD.4-8", "vcpu": 4, "ram": 8, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.40'), "monthly_price": Decimal('22500'), "price_currency": "ETB", "flavor_id": "ostd.4-8"},
            {"name": "OSTD.4-16", "vcpu": 4, "ram": 16, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.50'), "monthly_price": Decimal('30500'), "price_currency": "ETB", "flavor_id": "ostd.4-16"},
            {"name": "OSTD.8-16", "vcpu": 8, "ram": 16, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.60'), "monthly_price": Decimal('38700'), "price_currency": "ETB", "flavor_id": "ostd.8-16"},
            {"name": "OSTD.8-24", "vcpu": 8, "ram": 24, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.70'), "monthly_price": Decimal('46700'), "price_currency": "ETB", "flavor_id": "ostd.8-24"},
            {"name": "OSTD.12-24", "vcpu": 12, "ram": 24, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.80'), "monthly_price": Decimal('55100'), "price_currency": "ETB", "flavor_id": "ostd.12-24"},
            {"name": "OSTD.12-32", "vcpu": 12, "ram": 32, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('0.90'), "monthly_price": Decimal('63100'), "price_currency": "ETB", "flavor_id": "ostd.12-32"},
            {"name": "OSTD.16-32", "vcpu": 16, "ram": 32, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('1.00'), "monthly_price": Decimal('71500'), "price_currency": "ETB", "flavor_id": "ostd.16-32"},
            {"name": "OSTD.16-48", "vcpu": 16, "ram": 48, "os_storage": 30, "data_storage": 50, "hourly_price": Decimal('1.10'), "monthly_price": Decimal('87500'), "price_currency": "ETB", "flavor_id": "ostd.16-48"},
        ]
        for f in hardcoded_flavors:
            SubscriptionPlan.objects.update_or_create(
                flavor_id=f["flavor_id"],
                defaults={
                    'name': f["name"],
                    'vcpu': f["vcpu"],
                    'ram': f["ram"],
                    'os_storage': f["os_storage"],
                    'data_storage': f["data_storage"],
                    'hourly_price': f["hourly_price"],
                    'monthly_price': f["monthly_price"],
                    'price_currency': f["price_currency"],
                }
            )
        flavors = SubscriptionPlan.objects.all()

    form = ContactForm()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully!")
            return redirect("core:landing_page")

    context = {"form": form, "flavors": flavors}
    return render(request, "landing_page/landing.html", context)

def user_instances(request):
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
    if request.user.is_superuser:
        return redirect(reverse('core:billing_dashboard'))
    else:
        try:
            customer = Customer.objects.get(user=request.user)
            return redirect(reverse('core:customer_dashboard')) if customer.is_verified else redirect(reverse('core:customer_profile_create'))
        except Customer.DoesNotExist:
            return redirect(reverse('core:customer_profile_create'))

@login_required
@never_cache
def billing_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access the admin dashboard.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    context = user_instances(request)  # Assuming this function provides instance data
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

class CustomerDashboardView(LoginRequiredMixin, VerificationRequiredMixin, View):
    template_name = 'dashboard/customer/customer_dashboard.html'

    def get(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            context = user_instances(request)

            total_subscriptions = Subscription.objects.filter(customer=customer).count()
            total_invoices = Invoice.objects.filter(customer=customer).count()
            total_active_subscriptions = Subscription.objects.filter(customer=customer, status='active').count()
            recent_invoices = Invoice.objects.filter(customer=customer).order_by('-issue_date')[:5]
            pending_subscriptions = Subscription.objects.filter(customer=customer, status='pending')

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
                'pending_subscriptions': pending_subscriptions,
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

    def post(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            cart = Cart.objects.filter(user=request.user).first()

            if not cart or not cart.items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect('core:customer_dashboard')

            if not request.POST.get('terms'):
                messages.error(request, "You must agree to the terms and conditions.")
                return redirect('core:customer_dashboard')

            if not customer.is_verified:
                messages.error(request, "Please verify your email before confirming order.")
                return redirect('core:customer_dashboard')

            customer.terms_and_condition = True
            customer.save()

            created_subscriptions = []
            invoices = []
            days_map = {
                'monthly': 30,
                'quarterly': 90,
                'semi-annual': 180,
                'yearly': 365
            }
            tax_rate = Decimal('0.15')

            try:
                with transaction.atomic():
                    for item in cart.items.all():
                        days = days_map.get(item.billing_cycle, 30)
                        subscription = Subscription.objects.create(
                            customer=customer,
                            plan=item.plan,
                            status='pending',
                            start_date=timezone.now(),
                            end_date=timezone.now() + timedelta(days=days)
                        )
                        created_subscriptions.append(subscription)
                        amount = item.price
                        tax = amount * tax_rate
                        total = amount + tax
                        invoice = Invoice.objects.create(
                            customer=customer,
                            subscription=subscription,
                            amount=amount,
                            due_date=timezone.now() + timedelta(days=30),
                            issue_date=timezone.now(),
                            status='pending',
                            tax=tax,
                            total=total,
                            subtotal_currency='ETB',
                            tax_currency='ETB',
                            total_currency='ETB',
                        )
                        invoices.append(invoice)
                    cart.delete()
            except Exception as e:
                messages.error(request, f"Error processing order: {str(e)}")
                return redirect('core:customer_dashboard')

            if created_subscriptions:
                subject = "New Invoices Generated"
                message = render_to_string('emails/invoice_email.html', {
                    'user': request.user,
                    'invoices': invoices,
                    'subscriptions': created_subscriptions,
                    'invoice_url': request.build_absolute_uri(reverse('core:customer_invoices')),
                })
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [customer.user.email],
                    html_message=message,
                    fail_silently=False,
                )

            messages.success(request, f"Order placed successfully! {len(created_subscriptions)} subscription(s) created.")
            return redirect('core:customer_invoices')
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your dashboard.")
            return redirect('core:customer_profile_create')

class CustomerSubscriptionsView(LoginRequiredMixin, VerificationRequiredMixin, View):
    template_name = 'dashboard/customer/customer_subscriptions.html'

    def get(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            subscriptions = Subscription.objects.filter(customer=customer).select_related('plan').order_by('-start_date')

            # Handle pending subscription plan from session
            pending_plan_id = request.session.get('pending_subscription_plan_id')
            draft_subscription = None

            if pending_plan_id:
                try:
                    plan = SubscriptionPlan.objects.get(id=pending_plan_id)
                    draft_subscription, created = Subscription.objects.get_or_create(
                        customer=customer,
                        plan=plan,
                        status='pending',
                        defaults={
                            'start_date': timezone.now(),
                            'end_date': timezone.now() + timedelta(days=30)
                        }
                    )
                    if created:
                        messages.info(request, f"{plan.name} has been added to your pending subscriptions.")
                    if 'pending_subscription_plan_id' in request.session:
                        del request.session['pending_subscription_plan_id']
                except SubscriptionPlan.DoesNotExist:
                    messages.error(request, "Selected subscription plan is not available.")
                    if 'pending_subscription_plan_id' in request.session:
                        del request.session['pending_subscription_plan_id']

            context = {
                'subscriptions': subscriptions,
                'draft_subscription': draft_subscription,
                'customer': customer,
                'model_code': 'CustomerSubscriptions',
            }
            return render(request, self.template_name, context)
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your subscriptions.")
            return redirect('core:customer_profile_create')

    def post(self, request):
        action = request.POST.get('action')
        subscription_id = request.POST.get('subscription_id')

        if action == 'confirm' and subscription_id:
            try:
                subscription = Subscription.objects.get(
                    id=subscription_id,
                    customer__user=request.user,
                    status='pending'
                )
                invoice = Invoice.objects.create(
                    customer=subscription.customer,
                    subscription=subscription,
                    amount=subscription.plan.monthly_price,
                    due_date=timezone.now() + timedelta(days=30),
                    issue_date=timezone.now(),
                    status='pending',
                    tax=Decimal('0.00'),
                    total=subscription.plan.monthly_price,
                    subtotal_currency='ETB',
                    tax_currency='ETB',
                    total_currency='ETB',
                )

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
                    messages.warning(request, f"Subscription confirmed, but email sending failed: {str(e)}. Please contact support.")
                return redirect('core:customer_invoices')
            except Subscription.DoesNotExist:
                messages.error(request, "Invalid subscription or not authorized.")
        elif action == 'cancel' and subscription_id:
            try:
                subscription = Subscription.objects.get(
                    id=subscription_id,
                    customer__user=request.user,
                    status='pending'
                )
                subscription.delete()
                messages.success(request, "Pending subscription cancelled successfully.")
            except Subscription.DoesNotExist:
                messages.error(request, "Subscription not found.")

        return redirect('core:customer_subscriptions')

class CustomerInvoicesView(LoginRequiredMixin, VerificationRequiredMixin, View):
    template_name = 'dashboard/customer/customer_invoices.html'

    def get(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            invoices = Invoice.objects.filter(customer=customer).order_by('-issue_date')
            context = {
                'invoices': invoices,
                'model_code': 'CustomerInvoices',
            }
            return render(request, self.template_name, context)
        except Customer.DoesNotExist:
            messages.warning(request, "Please create a customer profile to view your invoices.")
            return redirect('core:customer_profile_create')

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, id=pk)
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
        if Customer.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a customer profile.")
            return redirect('core:customer_dashboard')

        # fields that exist in CustomUser
        initial_data = {
            'name': f"{request.user.first_name} {request.user.last_name}".strip() or "",
            'phone': request.user.phone_number or "",
            'company': request.user.company_name or "",
            'address': request.user.address or "",
            # Remove references to non-existent fields in CustomUser
            # 'city': request.user.city or "",  
            # 'state': request.user.state or "",  
            # 'country': request.user.country or "",  
            # 'tin_number': request.user.tin_number or "",  
            # 'preferred_payment_method': request.user.preferred_payment_method or "",  
        }

        form = CustomerForm(initial=initial_data)
        return render(request, self.template_name, {'form': form, 'model_code': 'CustomerProfile'})

    def post(self, request):
        if Customer.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a customer profile.")
            return redirect('core:customer_dashboard')

        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.user = request.user
                customer.is_verified = True
                customer.tenant_id = uuid4().hex
                customer.save()
                messages.success(request, "Customer profile created successfully.")

                # Handle pending subscription plan from session
                pending_plan_id = request.session.get('pending_subscription_plan_id')
                if pending_plan_id:
                    try:
                        plan = SubscriptionPlan.objects.get(id=pending_plan_id)
                        Subscription.objects.create(
                            customer=customer,
                            plan=plan,
                            status='pending',
                            start_date=timezone.now(),
                            end_date=self.calculate_end_date(plan)
                        )
                        messages.info(request, f"{plan.name} has been added to your pending subscriptions.")
                        if 'pending_subscription_plan_id' in request.session:
                            del request.session['pending_subscription_plan_id']
                    except SubscriptionPlan.DoesNotExist:
                        messages.error(request, "Selected subscription plan no longer available.")
                        if 'pending_subscription_plan_id' in request.session:
                            del request.session['pending_subscription_plan_id']

                # Transfer guest cart to authenticated user
                session_key = request.session.session_key
                guest_cart = Cart.objects.filter(session_id=session_key, user__isnull=True).first()
                if guest_cart:
                    cart, created = Cart.objects.get_or_create(
                        user=request.user,
                        session_id=None,
                        defaults={'created_at': timezone.now()}
                    )
                    for item in guest_cart.items.all():
                        CartItem.objects.create(
                            cart=cart,
                            plan=item.plan,
                            billing_cycle=item.billing_cycle,
                            price=item.price
                        )
                    guest_cart.delete()

                # Convert cart items to pending subscriptions
                cart = Cart.objects.filter(user=request.user).first()
                if cart and cart.items.exists():
                    days_map = {
                        'monthly': 30,
                        'quarterly': 90,
                        'semi-annual': 180,
                        'yearly': 365
                    }
                    for item in cart.items.all():
                        days = days_map.get(item.billing_cycle, 30)
                        Subscription.objects.get_or_create(
                            customer=customer,
                            plan=item.plan,
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

    def calculate_end_date(self, plan):
        start_date = timezone.now()
        days = {'monthly': 30, 'quarterly': 90, 'yearly': 365}.get(plan.billing_cycle, 30)
        return start_date + timedelta(days=days)

@login_required
def payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, customer__user=request.user)

    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method', 'manual')

        payment = Payment.objects.create(
            invoice=invoice,
            amount=invoice.total,
            payment_method=payment_method,
            transaction_id=transaction_id,
        )

        invoice.status = 'paid'
        invoice.save()

        if invoice.subscription and invoice.subscription.status == 'pending':
            subscription = invoice.subscription
            subscription.status = 'active'
            subscription.start_date = timezone.now()
            subscription.end_date = timezone.now() + timedelta(days=30)
            subscription.save()

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

        messages.success(request, "Payment successful! Your subscription is now active.")
        return redirect('core:customer_dashboard')

    context = {'invoice': invoice, 'model_code': 'Payment'}
    return render(request, 'dashboard/admin/payment.html', context)

def add_to_cart(request, plan_id=None):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id', plan_id)

    if not plan_id:
        messages.error(request, "No plan selected.")
        return redirect('core:landing_page')

    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    billing_multipliers = {
        'monthly': 1,
        'quarterly': 3,
        'semi-annual': 6,
        'yearly': 12,
    }
    multiplier = billing_multipliers.get(billing_cycle, 1)
    price = plan.monthly_price * multiplier

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
        # Store plan_id in session for guest users
        request.session['pending_subscription_plan_id'] = plan_id

    CartItem.objects.create(
        cart=cart,
        plan=plan,
        billing_cycle=billing_cycle,
        price=price
    )

    if request.user.is_authenticated:
        messages.success(request, f"{plan.name} added to cart!")
    else:
        messages.info(request, f"{plan.name} added to cart! Please login to checkout.")

    return redirect('core:cart_view')

def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        item = get_object_or_404(CartItem, id=item_id, cart__session_id=request.session.session_key)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('core:cart_view')

def cart_view(request):
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
        context = {'cart': cart, 'total': total, 'vat': vat, 'grand_total': grand_total}
    else:
        context = {'cart': None}

    if request.method == 'POST' and request.POST.get('action') == 'proceed_to_checkout':
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to proceed to checkout.")
            return redirect('accounts:login')
        elif not Customer.objects.filter(user=request.user).exists():
            messages.warning(request, "Please create a customer profile to proceed.")
            return redirect('core:customer_profile_create')
        else:
            return redirect('core:customer_dashboard')  # Redirect to dashboard for confirmation

    return render(request, 'cart.html', context)

@login_required
def checkout(request):
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
    def get(self, request, *args, **kwargs):
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
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, model_name):
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
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, model_name, pk):
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
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, model_name, pk):
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
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    # Prefetch related user and subscription data
    customers = Customer.objects.all().select_related('user').prefetch_related('subscription_set__plan')
    customer_data = []
    
    for customer in customers:
        # Get the most recent subscription (active or pending) for the customer
        subscription = customer.subscription_set.order_by('-start_date').first()
        customer_data.append({
            'customer': customer,
            'subscription': subscription
        })

    return render(request, 'dashboard/admin/customer_list.html', {
        'customer_data': customer_data,
        'model_code': 'Customer'
    })
@login_required
def customer_detail(request, customer_id):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    customer = get_object_or_404(Customer, id=customer_id)
    subscriptions = customer.subscription_set.select_related('plan').order_by('-start_date')
    invoices = customer.invoices.order_by('-issue_date')
    payments = Payment.objects.filter(invoice__customer=customer).order_by('-payment_date')
    # Fetch orders for the customer (via user)
    orders = Orders.objects.filter(user=customer.user).order_by('-created_at') if customer.user else []

    context = {
        'customer': customer,
        'subscriptions': subscriptions,
        'invoices': invoices,
        'payments': payments,
        'orders': orders,
        'model_code': 'CustomerDetail'
    }
    return render(request, 'dashboard/admin/customer_detail.html', context)
@login_required
def invoice_list(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    invoices = Invoice.objects.all().order_by('-issue_date')
    paginator = Paginator(invoices, 10)  # 10 invoices per page
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
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    plans = SubscriptionPlan.objects.all()
    return render(request, 'dashboard/admin/subscription_plan_list.html', {
        'plans': plans,
        'model_code': 'SubscriptionPlan'
    })

@login_required
def subscription_list(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('core:customer_dashboard') if request.user.is_staff else redirect('core:landing_page')

    subscriptions = Subscription.objects.select_related('customer__user', 'plan').all().order_by('-start_date')
    subscription_count = subscriptions.count()

    if subscription_count == 0:
        messages.info(request, "No subscriptions found. Customers may not have confirmed any subscriptions yet.")

    context = {
        'subscriptions': subscriptions,
        'model_code': 'Subscription',
        'subscription_count': subscription_count,
    }
    return render(request, 'dashboard/admin/subscription_list.html', context)

@login_required
def contact_submission_list(request):
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