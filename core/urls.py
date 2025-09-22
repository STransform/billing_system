from django.urls import path
from . import views
from .views import PricingView, DynamicPriceCreateView, DynamicPriceUpdateView, DynamicPriceDeleteView
urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("invoice/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("dashboard", views.dashboard, name="dashboard"),
    path('pricing/', PricingView.as_view(), name='price_config'),
    path('pricing/create/<str:model_name>/', DynamicPriceCreateView.as_view(), name='price_create'),
    path('pricing/update/<str:model_name>/<int:pk>/', DynamicPriceUpdateView.as_view(), name='price_update'),
    path('pricing/delete/<str:model_name>/<int:pk>/', DynamicPriceDeleteView.as_view(), name='price_delete'),
]
