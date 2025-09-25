from django import forms
from django.core.exceptions import ValidationError
from .models import ContactMessage, FlavorPrice, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice, Customer

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none",
                "placeholder": "Enter your name"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none",
                "placeholder": "Enter your email"
            }),
            "message": forms.Textarea(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none",
                "placeholder": "Write your message...",
                "rows": 4
            }),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'company', 'address', 'city', 'state', 'country', 'tin_number', 'preferred_payment_method']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Phone'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Company'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Country'}),
            'tin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter TIN Number'}),
            'preferred_payment_method': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select Payment Method'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.replace(" ", "").replace("-", "").isdigit():
            raise ValidationError("Phone number must contain only digits, spaces, or hyphens.")
        return phone

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise ValidationError("Name cannot be empty.")
        return name

class FlavorPriceForm(forms.ModelForm):
    class Meta:
        model = FlavorPrice
        fields = ['flavor_id', 'hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "flavor_id": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }

class VolumePriceForm(forms.ModelForm):
    class Meta:
        model = VolumePrice
        fields = ['volume_type_id', 'hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "volume_type_id": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }

class IpPriceForm(forms.ModelForm):
    class Meta:
        model = IpPrice
        fields = ['hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }

class RouterPriceForm(forms.ModelForm):
    class Meta:
        model = RouterPrice
        fields = ['hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }

class SnapShotPriceForm(forms.ModelForm):
    class Meta:
        model = SnapShotPrice
        fields = ['hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }

class ImagePriceForm(forms.ModelForm):
    class Meta:
        model = ImagePrice
        fields = ['hourly_price', 'monthly_price', 'price_currency']
        widgets = {
            "hourly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            "monthly_price": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none"
            }),
            'price_currency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 focus:border-red-500 focus:ring focus:ring-red-200 outline-none',
            }, choices=[
                ('ETB', 'ETB'),
            ]),
        }