from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from tutordudes.users.forms import UserChangeForm, UserCreationForm

User = get_user_model()


admin.site.register(User)
