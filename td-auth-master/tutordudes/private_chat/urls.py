from django.urls import path
from .views import private_chat_room, create_or_get_private_chat_room

app_name='private_chat'
urlpatterns = [
    path("", private_chat_room, name='private_chat_room'),
    path("room/", create_or_get_private_chat_room, name='create_or_get_private_chat_room'),
]
