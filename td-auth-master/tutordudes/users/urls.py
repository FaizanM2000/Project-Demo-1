from django.urls import path

from tutordudes.users.views import (
    UserRedirectView,
    UserUpdateView,
    user_detail,
    deactivate_account,
    activate_account,
    UserSubscriptionView,
    CancelSubscriptionView,
)

app_name = "users"
urlpatterns = [
    path("redirect/", UserRedirectView.as_view(), name="redirect"),
    path("update/", UserUpdateView.as_view(), name="update"),
    path("deactivate/", deactivate_account, name='deactivate'),
    path("activate/", activate_account, name='activate'),
    path("<user_id>/", user_detail, name='detail'),

    path("<str:username>/subscription/", UserSubscriptionView.as_view(), name='subscription'),
    path("<str:username>/subscription/cancel/", CancelSubscriptionView.as_view(), name="cancel-subscription"),
]
