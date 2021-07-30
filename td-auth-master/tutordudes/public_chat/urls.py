from django.urls import path

from .views import *
app_name='public_chat'

urlpatterns = [
    path("", home, name='public_chat'),
]
