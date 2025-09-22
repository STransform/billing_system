from django import forms
from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm

class TailwindFormMixin:
    """
    Mixin to automatically apply Tailwind CSS classes to form fields.
    """
    input_classes = (
        "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 "
        "focus:border-red-500 focus:ring focus:ring-red-200 outline-none "
    )
    textarea_classes = (
        "w-full px-4 py-3 rounded-lg bg-white text-black border border-gray-300 "
        "focus:border-red-500 focus:ring focus:ring-red-200 outline-none "
    )
    checkbox_classes = "h-4 w-4 text-red-600 border-gray-300 rounded"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            # Apply classes based on widget type
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", self.textarea_classes)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", self.checkbox_classes)
            elif isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput)):
                # Explicitly target common input types
                widget.attrs.setdefault("class", self.input_classes)


            if 'placeholder' not in widget.attrs:
                widget.attrs['placeholder'] = field.label.capitalize()


# 🔹 Registration form
class CustomUserCreationForm(TailwindFormMixin, UserCreationForm):
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your address"
        })
    )
    username = forms.CharField(
        label='Username',
        max_length=150,
        help_text=None,  
    )
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            "username", "email", "first_name", "last_name",
            "company_name", "address", "phone_number", "vat_number",
        )


# 🔹 Profile update form
class CustomUserChangeForm(TailwindFormMixin, UserChangeForm):
    password = None
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your address"
        })
    )
    class Meta(UserChangeForm.Meta):  
        model = CustomUser
        exclude = ["username"]
        fields = (
            "username", "email", "first_name", "last_name",
            "company_name", "address", "phone_number", "vat_number",
        )


# 🔹 Login form
class LoginForm(TailwindFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'class': self.input_classes, 'placeholder': 'Username'}
        )
        self.fields['password'].widget.attrs.update(
            {'class': self.input_classes, 'placeholder': 'Password'}
        )


class CustomPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    pass
