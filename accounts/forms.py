from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import CustomUser
from django.utils import timezone
from datetime import timedelta
import uuid

OPERATING_SYSTEMS = (
    ('ubuntu', (
        ('ubuntu_22_04_server', 'Ubuntu 22.04 Server'),
        ('ubuntu_24_04_server', 'Ubuntu 24.04 Server'),
        ('ubuntu_22_04_desktop', 'Ubuntu 22.04 Desktop'),
        ('ubuntu_24_04_desktop', 'Ubuntu 24.04 Desktop'),
    )),
    ('windows', (
        ('windows_server_2019', 'Windows Server 2019'),
        ('windows_desktop', 'Windows Desktop'),
    )),
)

class TailwindFormMixin:
    input_classes = (
        "w-full px-4 py-3 rounded-lg bg-gray-50 border-gray-300 "
        "focus:border-red-600 focus:ring focus:ring-red-600 focus:ring-opacity-20 outline-none"
    )
    textarea_classes = (
        "w-full px-4 py-3 rounded-lg bg-gray-50 border-gray-300 "
        "focus:border-red-600 focus:ring focus:ring-red-600 focus:ring-opacity-20 outline-none"
    )
    checkbox_classes = "h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", self.textarea_classes)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", self.checkbox_classes)
            elif isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput, forms.Select)):
                widget.attrs.setdefault("class", self.input_classes)
            if 'placeholder' not in widget.attrs and field.label:
                widget.attrs['placeholder'] = field.label.capitalize()

class CustomUserCreationForm(TailwindFormMixin, UserCreationForm):
    company_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Company Name'}),
    )
    address = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Address'}),
    )
    phone_number = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Phone Number'}),
    )
    city = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter City'}),
    )
    state = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter State'}),
    )
    country = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Country'}),
    )
    tin_number = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter TIN Number'}),
    )
    preferred_payment_method = forms.ChoiceField(
        choices=[
            ('bank_transfer', 'Bank Transfer'),
            ('telebirr', 'Telebirr'),
        ],
        widget=forms.Select(attrs={'placeholder': 'Select Payment Method'}),
        required=True
    )
    operating_system = forms.ChoiceField(
        choices=[('', 'Select Operating System')] + [(choice[0], choice[1]) for group in OPERATING_SYSTEMS for choice in group[1]],
        widget=forms.Select(attrs={'placeholder': 'Select Operating System'}),
        required=True
    )
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms of Service.'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email', 'password1', 'password2',
            'company_name', 'address', 'phone_number', 'city', 'state', 'country',
            'tin_number', 'preferred_payment_method', 'operating_system', 'terms'
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.replace(" ", "").replace("-", "").isdigit():
            raise ValidationError("Phone number must contain only digits, spaces, or hyphens.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already in use with a user account.")
        return email

    def save(self, commit=True):
        from core.models import Customer, Subscription, SubscriptionPlan
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_staff = True
        user.is_active = False
        if commit:
            with transaction.atomic():
                user.save()
                try:
                    customer = Customer.objects.get(user=user)
                except Customer.DoesNotExist:
                    customer = Customer.objects.create(
                        user=user,
                        name=f"{user.first_name} {user.last_name}".strip() or user.username,
                        phone=self.cleaned_data['phone_number'],
                        company=self.cleaned_data['company_name'],
                        address=self.cleaned_data['address'],
                        city=self.cleaned_data['city'],
                        state=self.cleaned_data['state'],
                        country=self.cleaned_data['country'],
                        tin_number=self.cleaned_data['tin_number'],
                        preferred_payment_method=self.cleaned_data['preferred_payment_method'],
                        operating_system=self.cleaned_data['operating_system'],
                        verification_token=uuid.uuid4().hex,
                        tenant_id=uuid.uuid4().hex,
                        is_verified=False
                    )
                if self.request and 'pending_subscription_plan_id' in self.request.session:
                    plan_id = self.request.session['pending_subscription_plan_id']
                    try:
                        plan = SubscriptionPlan.objects.get(id=plan_id)
                        if not Subscription.objects.filter(customer=customer, plan=plan).exists():
                            Subscription.objects.create(
                                customer=customer,
                                plan=plan,
                                status='pending',
                                start_date=timezone.now(),
                                end_date=self.calculate_end_date(plan)
                            )
                        del self.request.session['pending_subscription_plan_id']
                    except SubscriptionPlan.DoesNotExist:
                        pass
        return user

    def calculate_end_date(self, plan):
        start_date = timezone.now()
        days_map = {
            'monthly': 30,
            'quarterly': 90,
            'semi-annual': 180,
            'yearly': 365
        }
        days = days_map.get('monthly', 30)  # Default to monthly
        return start_date + timedelta(days=days)

class CustomUserChangeForm(TailwindFormMixin, UserChangeForm):
    password = None
    company_name = forms.CharField(required=False, widget=forms.TextInput, label="Company")
    address = forms.CharField(required=False, widget=forms.TextInput)
    phone_number = forms.CharField(required=False, widget=forms.TextInput)
    city = forms.CharField(required=False, widget=forms.TextInput)
    state = forms.CharField(required=False, widget=forms.TextInput)
    country = forms.CharField(required=False, widget=forms.TextInput)
    tin_number = forms.CharField(required=False, widget=forms.TextInput, label="TIN Number")
    preferred_payment_method = forms.ChoiceField(
        choices=[
            ('', 'Select Payment Method'),
            ('bank_transfer', 'Bank Transfer'),
            ('telebirr', 'Telebirr'),
        ],
        required=False,
        widget=forms.Select
    )
    operating_system = forms.ChoiceField(
        choices=[('', 'Select Operating System')] + [(choice[0], choice[1]) for group in OPERATING_SYSTEMS for choice in group[1]],
        required=False,
        widget=forms.Select
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'is_active', 'is_staff',
            'company_name', 'address', 'phone_number', 'city', 'state', 'country',
            'tin_number', 'preferred_payment_method', 'operating_system'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.replace(" ", "").replace("-", "").isdigit():
            raise ValidationError("Phone number must contain only digits, spaces, or hyphens.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            raise ValidationError("This email is already in use with another user account.")
        return email

class LoginForm(TailwindFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Password'})

class CustomPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    pass