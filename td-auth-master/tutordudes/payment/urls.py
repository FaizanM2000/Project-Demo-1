from django.urls import path
from django.views.generic import TemplateView

from .views import (
    get_publishable_key,
    SubscriptionView,
    CreateCheckoutSessionView,
    payment_success,
    CustomerPortalView,
    webhook,
    payment_canceled,
)


app_name='payment'
urlpatterns = [
    path('subscription/', SubscriptionView.as_view(), name='plan'),
    path('setup/', get_publishable_key, name='setup'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(),  name='create-checkout-session'),
    path('success/', payment_success, name='payment_success'),
    path('canceled/', payment_canceled, name='payment_canceled'),
    path('customer-portal/', CustomerPortalView.as_view(), name='customer-portal'),
    path('webhook/', webhook, name='webhook'),
]
