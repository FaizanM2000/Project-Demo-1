from django.urls import path
from .views import (
    send_friend_request,
    friend_requests,
    accept_friend_request,
    remove_friend,
    decline_friend_request,
    cancel_friend_request,
    friend_list,
)

app_name='friend'
urlpatterns = [
    path("send_friend_request/", send_friend_request, name='send_friend_request'),
    path("friend_requests/<int:user_id>/", friend_requests, name='friend_requests'),
    path("accept_friend_request/<int:friend_request_id>/", accept_friend_request, name='accept_friend_request'),
    path("decline_friend_request/<int:friend_request_id>/", decline_friend_request, name='decline_friend_request'),
    path("cancel_friend_request/", cancel_friend_request, name='cancel_friend_request'),
    path("remove_friend/", remove_friend, name='remove_friend'),
    path("friend_list/<int:user_id>/", friend_list, name='friend_list'),
]
