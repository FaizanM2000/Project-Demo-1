from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404


class ServicePermissionMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')

        status = ("active", "trialing")
        if request.user.subscription.status in status:
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('payment:plan')
