from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from django.urls import path
from tutordudes.public_chat.consumers import PublicChatConsumer
from tutordudes.private_chat.consumers import PrivateChatConsumer
from tutordudes.notification.consumers import NotificationConsumer

application = ProtocolTypeRouter({
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                path("public_chat/<room_id>/", PublicChatConsumer.as_asgi()),
                path("private_chat/<room_id>/", PrivateChatConsumer.as_asgi()),
                path("notifications/", NotificationConsumer.as_asgi()),
            ])
        ),
    ),
})
