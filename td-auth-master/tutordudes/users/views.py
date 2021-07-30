from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView, UpdateView, FormView, DetailView
from django.contrib import messages
from .forms import CancelSubscriptionForm
from django.http import HttpResponse
from django.shortcuts import render

from tutordudes.friend.friend_request_status import FriendRequestStatus
from tutordudes.friend.models import FriendList, FriendRequest
from tutordudes.friend.utils import get_friend_request

import stripe


stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


def user_detail(request, *args, **kwargs):
    context = {}
    user_id = kwargs.get('user_id')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponse("User does not exist!")

    # current user profile
    context['user'] = user

    # current user friend list
    try:
        friend_list = FriendList.objects.get(user=user)
    except FriendList.DoesNotExist:
        friend_list = FriendList(user=user)
        friend_list.save()

    friends = friend_list.friends.all()
    context['friends'] = friends

    is_self = True
    is_friend = False
    request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
    friend_requests = None
    if request.user.is_authenticated and user != request.user:
        is_self = False
        if friends.filter(pk=request.user.id):
            is_friend = True
        else:
            # 1 them sent you friend request
            if get_friend_request(sender=user, receiver=request.user):
                request_sent = FriendRequestStatus.THEM_SENT_TO_YOU.value
                context['pending_friend_request_id'] = get_friend_request(sender=user, receiver=request.user).id
            # 2 you sent them friend request
            elif get_friend_request(sender=request.user, receiver=user):
                request_sent = FriendRequestStatus.YOU_SENT_TO_THEM.value
            # 3 no friend request between you and current user
            else:
                request_sent = FriendRequestStatus.NO_REQUEST_SENT.value

    elif not request.user.is_authenticated:
        is_self = False

    else:
        try:
            friend_requests = FriendRequest.objects.filter(receiver=request.user, is_active=True)
        except:
            pass

    context['is_self'] = is_self
    context['is_friend'] = is_friend
    context['request_sent'] = request_sent
    context['friend_requests'] = friend_requests
    context['BASE_URL'] = settings.DOMAIN
    return render(request, 'users/user_detail.html', context=context)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ['username', 'profile_image']
    template_name = 'users/user_form.html'

    def get_success_url(self):
        return reverse("users:update")

    def get_object(self, queryset=None):
        return self.request.user


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('home')


@login_required
def deactivate_account(request):
    request.user.is_active = False
    request.user.save()
    return redirect('account_login')


def activate_account(request):
    email = request.POST.get('email', None)
    try:
        user = User.objects.get(email=email)
    except:
        message = 'You email has not been registered. Please sign up first!'
        messages.info(request, message)
        return redirect('account_signup')
    else:
        user.is_active = True
        user.save()
        messages.info(request, "You account has been activated.")
        return redirect('home')


class UserSubscriptionView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_subscription.html"


class CancelSubscriptionView(LoginRequiredMixin, FormView):
    form_class = CancelSubscriptionForm

    def get_success_url(self):
        return reverse("payment:plan")

    def form_valid(self, form):
        stripe.Subscription.delete(self.request.user.subscription.stripe_subscription_id)
        messages.success(self.request, "You have successfully cancelled your subscription")
        return super().form_valid(form)
