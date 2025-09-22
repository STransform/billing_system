from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView
from django.shortcuts import redirect
from .forms import CustomPasswordChangeForm, CustomUserCreationForm, LoginForm, CustomUserChangeForm
from .models import CustomUser
from openstack import connection
from django.views import View


conn = connection.from_config(cloud_name="kolla-admin")
# 🔹 Register
class RegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")


# 🔹 Login
class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        # Store project_id in session
        cloud_user = conn.identity.find_user(user.username)
        if cloud_user and "default_project_id" in cloud_user:
            self.request.session["project_id"] = cloud_user["default_project_id"]

        login(self.request, user)

        # Redirect to `next` param or dashboard
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return redirect(next_url or reverse_lazy("dashboard"))


# 🔹 Logout
class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        request.session.flush()
        return redirect(reverse_lazy("accounts:login"))


# 🔹 Profile View
class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = "accounts/profile.html"
    context_object_name = "user"

    def get_object(self, queryset=None):
        return self.request.user


# 🔹 Profile (edit/update)
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