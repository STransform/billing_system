from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path('sync-subscription-plans/', views.sync_subscription_plans_view, name='sync_subscription_plans'), 
    
    path("invoice/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("billing-dashboard/", views.billing_dashboard, name="billing_dashboard"),
    path("customer-dashboard/", views.CustomerDashboardView.as_view(), name="customer_dashboard"),
    path("customer-profile/create/", views.CustomerProfileCreateView.as_view(), name="customer_profile_create"),
    path("customer-subscriptions/", views.CustomerSubscriptionsView.as_view(), name="customer_subscriptions"),
    path('customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path("customer-invoices/", views.CustomerInvoicesView.as_view(), name="customer_invoices"),
    path("pricing/", views.PricingView.as_view(), name="price_configuration"),
    path("pricing/create/<str:model_name>/", views.DynamicPriceCreateView.as_view(), name="price_create"),
    path("pricing/update/<str:model_name>/<int:pk>/", views.DynamicPriceUpdateView.as_view(), name="price_update"),
    path("pricing/delete/<str:model_name>/<int:pk>/", views.DynamicPriceDeleteView.as_view(), name="price_delete"),
    path("add_to_cart/<int:plan_id>/", views.add_to_cart, name="add_to_cart"),
    path("remove_from_cart/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/", views.cart_view, name="cart_view"),
    path("checkout/", views.checkout, name="checkout"),
    path("payment/<int:invoice_id>/", views.PaymentView.as_view(), name="payment"),
    path("customer_list/", views.customer_list, name="customer_list"),
    path('customers/detail/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail_view'),
    path("admin-invoices/", views.invoice_list, name="invoice_list"),
    path("subscription-plans/", views.subscription_plan_list, name="subscription_plan_list"),
    path("subscriptions/", views.subscription_list, name="subscription_list"),
    path("contact-submissions/", views.contact_submission_list, name="contact_submission_list"),
    path('subscriptions/detail/<int:pk>/', views.AdminSubscriptionDetailView.as_view(), name='admin_subscription_detail'),
    path('invoice/<int:pk>/download-pdf/', views.download_invoice_pdf, name='download_invoice_pdf'),
]