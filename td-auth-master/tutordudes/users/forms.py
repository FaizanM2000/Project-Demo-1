from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django import forms
from django.utils.translation import gettext_lazy as _
from django import forms as normal_forms


User = get_user_model()


class CancelSubscriptionForm(normal_forms.Form):
    hidden = normal_forms.HiddenInput()


class UserChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(admin_forms.UserCreationForm):
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }
