import time

from django.core.paginator import Paginator
from django.core.serializers.python import Serializer
from django.utils import timezone
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from tutordudes.private_chat.models import PrivateChatRoom, PrivateChatMessage, UnreadChatMessage
from tutordudes.friend.models import FriendList
from tutordudes.users.utils import LazyUserEncoder
import json
import asyncio

from .utils import (
    ClientError, calculate_timestamp, MSG_TYPE_MESSAGE,
    MSG_TYPE_USERS_COUNT, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE, MSG_TYPE_ENTER, MSG_TYPE_LEAVE
)
from ..users.models import User


class PrivateChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        print("ChatConsumer: connect: " + str(self.scope["user"]))

        # let everyone connect. But limit read/write to authenticated users
        await self.accept()

        # the room_id will define what it means to be "connected". If it is not None, then the user is connected.
        self.room_id = None

    async def receive_json(self, content, **kwargs):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        print("ChatConsumer: receive_json")
        command = content.get("command", None)
        try:
            if command == "join":
                await self.join_room(content['room_id'])
            elif command == "leave":
                await self.leave_room(content['room_id'])

            elif command == "send":
                message = content['message']
                room_id = content['room_id']
                if message and len(message.lstrip()) != 0:
                    await self.send_room(room_id, message)

            elif command == "retrieve":
                await self.display_progress_bar(True)

                room = await get_room_or_error(content['room_id'], self.scope['user'])
                payload = await get_room_chat_messages(room, content['page_number'])
                if payload:
                    payload = json.loads(payload)
                    await self.send_messages_payload(payload['messages'], payload['new_page_number'])
                else:
                    raise ClientError(204, "Something went wrong when retrieving private chat messages")

                await self.display_progress_bar(False)

            elif command == "user":
                await self.display_progress_bar(True)

                room = await get_room_or_error(content['room_id'], self.scope['user'])
                payload = get_user_info(room, self.scope['user'])
                if payload:
                    payload = json.loads(payload)
                    await self.send_user_info_payload(payload['user_info'])
                else:
                    raise ClientError(422, "Something went wrong when retrieving user info")

                await self.display_progress_bar(False)
        except ClientError as e:
            await self.display_progress_bar(False)
            await self.handle_client_error(e)

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave the room
        print("ChatConsumer: disconnect")
        try:
            if self.room_id:
                await self.leave_room(self.room_id)
        except Exception as e:
            pass

    async def join_room(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware (AuthMiddlewareStack)
        print("ChatConsumer: join_room: " + str(room_id))
        try:
            room = await get_room_or_error(room_id, self.scope['user'])
        except ClientError as e:
            return await self.handle_client_error(e)

        await connect_user(room, self.scope["user"])

        # store current room id
        self.room_id = room.id

        await on_user_connected(room, self.scope["user"])

        # add them to the group to get messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name
        )

        await self.send_json({
            'join': str(room.id)
        })

        await self.channel_layer.group_send(
            room.group_name,
            {
                'type': "chat.join",  # chat_join
                'room_id': room.id,
                'profile_image': self.scope['user'].profile_image.url,
                'username': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )

    async def leave_room(self, room_id):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        print("ChatConsumer: leave_room")
        room = await get_room_or_error(room_id, self.scope['user'])

        # Remove user from "connected_users" list
        await disconnect_user(room, self.scope["user"])

        # notify other users
        await self.channel_layer.group_send(
            room.group_name,
            {
                'type': 'chat.leave',  # chat_leave
                'room_id': room_id,
                'profile_image': self.scope['user'].profile_image.url,
                'username': self.scope['user'].username,
                'user_id': self.scope['user'].id
            }
        )

        # reset room id
        self.room_id = None

        # remove from group
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name
        )

        # update leave state
        await self.send_json({
            'leave': str(room_id)
        })

    async def send_room(self, room_id, message):
        """
        Called by receive_json when someone sends a message to a room.
        """
        print("ChatConsumer: send_room")
        if self.room_id:
            if str(room_id) != str(self.room_id):
                raise ClientError(422, "Room access denied")
        else:
            raise ClientError(422, "Room access denied")

        # Get the room and send to the group about it
        room = await get_room_or_error(room_id, self.scope["user"])

        # get list of connected_users
        connected_users = room.connected_users.all()

        # Execute these functions asychronously
        await asyncio.gather(*[
            append_unread_msg_if_not_connected(room, room.user1, connected_users, message),
            append_unread_msg_if_not_connected(room, room.user2, connected_users, message),
            save_private_chat_message(room, self.scope["user"], message)
        ])

        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",  # chat_message
                "profile_image": self.scope['user'].profile_image.url,
                "username": self.scope['user'].username,
                "user_id": self.scope['user'].id,
                "message": str(message),
            }  # ---> chat_message(self, event) event
        )

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    async def chat_join(self, event):
        """
        Called when someone has joined our chat.
        """
        # Send a message down to the client
        print("ChatConsumer: chat_join: " + str(self.scope["user"].id))
        if event['username']:
            await self.send_json({
                "msg_type": MSG_TYPE_ENTER,
                "room_id": event['room_id'],
                "profile_image": event['profile_image'],
                "username": event['username'],
                "user_id": event['user_id'],
                "message": event['username'] + " connected.",
            })

    async def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        print("ChatConsumer: chat_leave")
        if event['username']:
            await self.send_json({
                "msg_type": MSG_TYPE_LEAVE,
                "room_id": event['room_id'],
                "profile_image": event['profile_image'],
                "username": event['username'],
                "user_id": event['user_id'],
                "message": event['username'] + " disconnected.",
            })

    async def chat_message(self, event):
        print("ChatConsumer: chat_message")
        timestamp = calculate_timestamp(timezone.now())
        await self.send_json({
            "msg_type": MSG_TYPE_MESSAGE,
            "profile_image": event['profile_image'],
            "username": event['username'],
            "user_id": event['user_id'],
            "message": event['message'],
            "timestamp": timestamp,
        })

    async def send_messages_payload(self, messages, new_page_number):
        """
        Send a payload of messages to the ui
        """
        print("ChatConsumer: send_messages_payload. ")
        await self.send_json({
            "messages_payload": "messages_payload",
            "messages": messages,
            "new_page_number": new_page_number
        })

    async def send_user_info_payload(self, user_info):
        """
        Send a payload of user information to the ui
        """
        print("ChatConsumer: send_user_info_payload. ")
        await self.send_json({
            'user_info': user_info,
        })

    async def display_progress_bar(self, display_progress_bar):
        """
        1. is_displayed = True
            - Display the progress bar on UI
        2. is_displayed = False
            - Hide the progress bar on UI
        """
        await self.send_json({
            'display_progress_bar': display_progress_bar,
        })

    async def handle_client_error(self, e):
        error = {}
        error['error'] = e.code
        error['message'] = e.message
        await self.send_json(error)


@database_sync_to_async
def get_room_or_error(room_id, user):
    '''
    try to fetch room for given user
    '''
    try:
        room = PrivateChatRoom.objects.get(id=room_id)
    except PrivateChatRoom.DoesNotExist:
        raise ClientError(422, "Invalid room")

    # is user allowed into the room ?
    if user != room.user1 and user != room.user2:
        raise ClientError(422, "You has no permission to start this chat")

    friends = FriendList.objects.get(user=user).friends.all()
    if not room.user1 in friends:
        if not room.user2 in friends:
            raise ClientError(422, "You must be friends before private chat")
    return room


def get_user_info(room, user):
    '''
    retrieve the user info you are chatting with
    '''
    # time.sleep(1)
    try:
        other_user = room.user1
        if user == other_user:
            other_user = room.user2

        payload = {}
        s = LazyUserEncoder()
        payload['user_info'] = s.serialize([other_user])[0]
        return json.dumps(payload)
    except ClientError as e:
        print("ClientError: " + str(e))

    return None


@database_sync_to_async
def save_private_chat_message(room, user, message):
    PrivateChatMessage.objects.create(user=user, room=room, message=message)


class LazyRoomChatMessageEncoder(Serializer):

    def get_dump_object(self, obj):
        dump_object = {}
        dump_object.update({'msg_type': MSG_TYPE_MESSAGE})
        dump_object.update({'user_id': str(obj.user.id)})
        dump_object.update({'username': str(obj.user.username)})
        dump_object.update({'message': str(obj.message)})
        dump_object.update({'profile_image': str(obj.user.profile_image.url)})
        dump_object.update({'timestamp': calculate_timestamp(obj.timestamp)})
        dump_object.update({'msg_id': str(obj.id)})
        return dump_object


@database_sync_to_async
def get_room_chat_messages(room, page_number):
    try:
        qs = PrivateChatMessage.objects.by_room(room)
        p = Paginator(qs, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE)

        payload = {}
        new_page_number = int(page_number)
        if new_page_number <= p.num_pages:
            new_page_number = new_page_number + 1
            s = LazyRoomChatMessageEncoder()
            payload['messages'] = s.serialize(p.page(page_number).object_list)
        else:
            payload['messages'] = "None"

        payload['new_page_number'] = new_page_number
        return json.dumps(payload)

    except ClientError as e:
        print("get_room_chat_messages EXCEPTION: " + str(e))
        return None


@database_sync_to_async
def connect_user(room, user):
    # add user to connected_users list
    account = User.objects.get(pk=user.id)
    return room.connect_user(account)


@database_sync_to_async
def disconnect_user(room, user):
    # remove from connected_users list
    user = User.objects.get(pk=user.id)
    return room.disconnect_user(user)


# If the user is not connected to the chat, increment "unread messages" count
@database_sync_to_async
def append_unread_msg_if_not_connected(room, user, connected_users, message):
    if not user in connected_users:
        try:
            unread_msgs = UnreadChatMessage.objects.get(room=room, user=user)
            unread_msgs.most_recent_message = message
            unread_msgs.count += 1
            unread_msgs.save()
        except UnreadChatMessage.DoesNotExist:
            UnreadChatMessage(room=room, user=user, count=1).save()
            pass
    return


# When a user connects, reset their unread message count
@database_sync_to_async
def on_user_connected(room, user):
    # confirm they are in the connected users list
    connected_users = room.connected_users.all()
    if user in connected_users:
        try:
            # reset count
            unread_msgs = UnreadChatMessage.objects.get(room=room, user=user)
            unread_msgs.count = 0
            unread_msgs.save()
        except UnreadChatMessage.DoesNotExist:
            UnreadChatMessage(room=room, user=user).save()
            pass
    return







