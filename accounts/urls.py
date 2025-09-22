from django.urls import path
from .views import (
    RegisterView, CustomLoginView, CustomLogoutView,
    ProfileView, ProfileEditView, CustomPasswordChangeView
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile_edit"),
    path("password/change/", CustomPasswordChangeView.as_view(), name="password_change"),
]
