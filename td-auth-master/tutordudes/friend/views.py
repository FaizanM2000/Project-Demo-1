from django.shortcuts import render, redirect
from django.http import HttpResponse
from tutordudes.users.models import User
from tutordudes.friend.models import FriendList, FriendRequest
import json


def send_friend_request(request, *args, **kwargs):
    payload = {}
    if request.method == 'POST' and request.user.is_authenticated:
        sender = request.user
        user_id = request.POST.get('receiver_user_id')
        if user_id:
            receiver = User.objects.get(id=user_id)
            try:
                friend_requests = FriendRequest.objects.filter(sender=sender, receiver=receiver)
                try:
                    for request in friend_requests:
                        if request.is_active:
                            raise Exception("You have already sent them friend request")
                    friend_request = FriendRequest(sender=sender, receiver=receiver)
                    friend_request.save()
                    payload['response'] = "Friend request sent"
                except Exception as e:
                    payload['response'] = str(e)

            except FriendRequest.DoesNotExist:
                friend_request = FriendRequest(sender=sender, receiver=receiver)
                friend_request.save()
                payload['response'] = "Friend request sent"

            if payload['response'] == None:
                payload['response'] = 'Something went wrong'

        else:
            payload['response'] = "User cannot be found"
    else:
        payload['response'] = "Please login first to send friend request"

    return HttpResponse(json.dumps(payload), content_type='application/json')


def friend_requests(request, *args, **kwargs):
    context = {}
    if request.user.is_authenticated:
        user_id = kwargs['user_id']
        user = User.objects.get(id=user_id)
        if user == request.user:
            friend_requests = FriendRequest.objects.filter(receiver=user, is_active=True)
            context['friend_requests'] = friend_requests
        else:
            return HttpResponse("You cannot view another user friend requests.")
    else:
        return redirect("account_login")

    return render(request, 'friend/friend_requests.html', context=context)


def accept_friend_request(request, *args, **kwargs):
    payload = {}
    if request.method == 'GET' and request.user.is_authenticated:
        friend_request_id = kwargs['friend_request_id']
        if friend_request_id:
            try:
                friend_request = FriendRequest.objects.get(id=friend_request_id)
            except FriendRequest.DoesNotExist:
                payload['response'] = 'Friend request cannot be found'
            else:
                if friend_request.receiver == request.user:
                    friend_request.accept()
                    payload['response'] = 'Friend request accepted'
                else:
                    payload['response'] = 'That is not your friend request to be accepted'
        else:
            payload['response'] = 'Friend request cannot be found'
    else:
        payload['response'] = 'Please login first to accept your friend request'

    return HttpResponse(json.dumps(payload), content_type='application/json')


def remove_friend(request, *args, **kwargs):
    payload = {}
    if request.method == 'POST' and request.user.is_authenticated:
        user_id = request.POST['receiver_user_id']
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                friend_list = FriendList.objects.get(user=request.user)
                friend_list.unfriend(user)
                payload['response'] = 'Remove friend successfully'
            except Exception as e:
                payload['response'] = 'Something went wrong: ' + str(e)
        else:
            payload['response'] = 'Friend not found'
    else:
        payload['response'] = 'Please login first to remove your friend'

    return HttpResponse(json.dumps(payload), content_type='application/json')


def decline_friend_request(request, *args, **kwargs):
    payload = {}
    if request.method == 'GET' and request.user.is_authenticated:
        friend_request_id = kwargs['friend_request_id']
        if friend_request_id:
            friend_request = FriendRequest.objects.get(id=friend_request_id)
            if friend_request.receiver == request.user and friend_request.is_active:
                friend_request.decline()
                payload['response'] = 'Friend request declined'
            else:
                payload['response'] = 'Friend request is invalid'
        else:
            payload['response'] = 'Friend request cannot be found'

    else:
        payload['response'] = 'Please login first to decline friend request'
    return HttpResponse(json.dumps(payload), content_type='application/json')


def cancel_friend_request(request, *args, **kwargs):
    payload = {}
    if request.method == 'POST' and request.user.is_authenticated:
        sender = request.user
        user_id = request.POST['receiver_user_id']
        if user_id:
            receiver = User.objects.get(id=user_id)
            try:
                friend_requests = FriendRequest.objects.filter(sender=sender, receiver=receiver, is_active=True)
            except Exception as e:
                payload['response'] = 'Nothing to cancel'
            else:
                for request in friend_requests:
                    request.cancel()
                payload['response'] = 'Friend request cancelled'

        else:
            payload['response'] = 'Friend request cannot be found'

    else:
        payload['response'] = 'Please login first to cancel friend request'
    return HttpResponse(json.dumps(payload), content_type='application/json')


def friend_list(request, *args, **kwargs):
    context = {}
    user = request.user
    if user.is_authenticated:
        user_id = kwargs.get("user_id")
        if user_id:
            try:
                this_user = User.objects.get(id=user_id)
                context['this_user'] = this_user
            except User.DoesNotExist:
                return HttpResponse("That user does not exist")

            try:
                friend_list = FriendList.objects.get(user=this_user)
            except FriendList.DoesNotExist:
                return HttpResponse("That user has no friend list")
            if user != this_user:
                if not user in friend_list.friends.all():
                    return HttpResponse("You must be their friends to view their friends list")

            friends = []  # [(friend, is_friend), (friend, False)]
            auth_friend_list = FriendList.objects.get(user=user)
            for friend in friend_list.friends.all():
                friends.append((friend, auth_friend_list.is_mutual_friend(friend)))
            context['friends'] = friends
        else:
            return HttpResponse("That user does not exist")

    else:
        return HttpResponse("Please login first to see friend list")

    return render(request, 'friend/friend_list.html', context=context)













