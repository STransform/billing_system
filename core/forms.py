from django import forms
from .models import ContactMessage
from .models import FlavorPrice, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice

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