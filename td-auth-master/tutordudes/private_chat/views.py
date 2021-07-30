from itertools import chain
import json
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from .models import PrivateChatRoom, PrivateChatMessage
from tutordudes.users.models import User
from .utils import get_or_create_private_chat_room
from tutordudes.friend.models import FriendList
from datetime import datetime
import pytz


def private_chat_room(request, *args, **kwargs):
    room_id = request.GET.get('room_id')
    if request.user.is_authenticated:
        context = {}
        context['m_and_f'] = get_recent_chatroom_messages(request.user)
        context["DOMAIN"] = settings.DOMAIN
        context['debug_mode'] = settings.DEBUG
        if room_id:
            context["room_id"] = room_id

        return render(request, "chat/private_chat_room.html", context)
    else:
        return redirect("account_login")


def get_recent_chatroom_messages(user):
    """
	sort in terms of most recent chats (users that you most recently had conversations with)
	"""
    # 1. Find all the rooms this user is a part of
    rooms1 = PrivateChatRoom.objects.filter(user1=user, is_active=True)
    rooms2 = PrivateChatRoom.objects.filter(user2=user, is_active=True)

    # 2. merge the lists
    rooms = list(chain(rooms1, rooms2))

    # 3. find the newest msg in each room
    m_and_f = []
    for room in rooms:
        # Figure out which user is the "other user" (aka friend)
        if room.user1 == user:
            friend = room.user2
        else:
            friend = room.user1

        # confirm you are even friends (in case chat is left active somehow)
        friend_list = FriendList.objects.get(user=user)
        if not friend_list.is_mutual_friend(friend):
            chat = get_or_create_private_chat_room(user, friend)
            chat.is_active = False
            chat.save()
        else:
            # find newest msg from that friend in the chat room
            try:
                message = PrivateChatMessage.objects.filter(room=room, user=friend).latest("timestamp")
            except PrivateChatMessage.DoesNotExist:
                # create a dummy message with dummy timestamp
                today = datetime(
                    year=1950,
                    month=1,
                    day=1,
                    hour=1,
                    minute=1,
                    second=1,
                    tzinfo=pytz.UTC
                )
                message = PrivateChatMessage(
                    user=friend,
                    room=room,
                    timestamp=today,
                    message="",
                )
            m_and_f.append({
                'message': message,
                'friend': friend
            })
    return sorted(m_and_f, key=lambda x: x['message'].timestamp, reverse=True)


# Ajax call to return a private chatroom or create one if does not exist
def create_or_get_private_chat_room(request, *args, **kwargs):
    user1 = request.user
    payload = {}
    if user1.is_authenticated:
        if request.method == 'POST':
            user2_id = request.POST['user2_id']
            try:
                user2 = User.objects.get(id=user2_id)
                chat = get_or_create_private_chat_room(user1, user2)
                payload['response'] = "success"
                payload['room_id'] = chat.id
            except User.DoesNotExist:
                payload['response'] = 'User cannot be found'
    else:
        payload['response'] = 'Please login first to start private chat'

    return HttpResponse(json.dumps(payload), content_type='application/json')
