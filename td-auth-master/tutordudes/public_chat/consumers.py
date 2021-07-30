from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PublicChatRoom, PublicChatMessage
from channels.db import database_sync_to_async
from django.core.serializers.python import Serializer
from django.core.paginator import Paginator
from django.core.serializers import serialize
from tutordudes.private_chat.utils import ClientError, calculate_timestamp, MSG_TYPE_MESSAGE, MSG_TYPE_USERS_COUNT, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE
import json

User = get_user_model()


class PublicChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        '''
        websocket handshake call connect
        '''
        print("Public chat consumer connect: " + str(self.scope['user']))
        await self.accept()
        self.room_id = None


    async def disconnect(self, code):
        '''
        websocket close call disconnect
        '''
        print("Public chat consumer disconnect: " + str(self.scope['user']))
        try:
            if self.room_id:
                await self.leave_room(self.room_id)
        except ClientError:
            pass

    async def receive_json(self, content, **kwargs):
        '''
        when payload sent, channels will receive/decode it as json content, then call receive_json
        '''
        command = content.get("command", None)
        message = content.get("message", None)
        room_id = content.get("room_id", None)
        print("Public chat receive_json command: " + str(command))
        print("Public chat receive_json message: " + str(message))
        print("Public chat receive_json room_id: " + str(room_id))

        try:
            if command == 'send':
                if not message or len(message.lstrip()) == 0:
                    raise ClientError(422, "You cannot send empty message")

                await self.send_room(room_id, message)
            elif command == 'join':
                await self.join_room(room_id)
            elif command == 'leave':
                await self.leave_room(room_id)
            elif command == 'retrieve':
                await self.display_progress_bar(True)

                room = await get_room_or_error(room_id)
                payload = await get_room_chat_messages(room, content['page_number'])
                if payload:
                    payload = json.loads(payload)
                    await self.send_messages_payload(payload['messages'], payload['new_page_number'])
                else:
                    raise ClientError(204, "Something went wrong when retrieving chat room messages")

                await self.display_progress_bar(False)

        except ClientError as e:
            await self.display_progress_bar(False)
            await self.handle_client_error(e)  # only user can see that error msg, other user in the same group cannot because message has not been sent into group

    async def send_room(self, room_id, message):
        '''
        when someone send a message to room, will be called by receive_json
        '''
        print("Public chat send_room: ")
        if self.room_id:
            if str(room_id) != str(self.room_id):
                raise ClientError(422, "Room access denied")
            if not self.scope['user'].is_authenticated:
                raise ClientError(422, "You must login to chat")
        else:
            raise ClientError(422, "Room access denied")

        room = await get_room_or_error(room_id)
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",  # chat_message
                "profile_image": self.scope['user'].profile_image.url,
                "username": self.scope['user'].username,
                "user_id": self.scope['user'].id,
                "message": message,
            }  # ---> chat_message(self, event) event
        )
        await save_public_room_chat_message(room, self.scope['user'], message)

    async def chat_message(self, event):
        '''
        when someone sent message into group, will be called to send message to client
        '''
        print("Public chat chat_message from user: " + str(event['user_id']))
        timestamp = calculate_timestamp(timezone.now())
        await self.send_json({
            "msg_type": MSG_TYPE_MESSAGE,
            "profile_image": event['profile_image'],
            "username": event['username'],
            "user_id": event['user_id'],
            "message": event['message'],
            "timestamp": timestamp,
        })

    async def join_room(self, room_id):
        '''
        when someone sent JOIN command, will be called by receive_json()
        '''
        print("Public chat join_room: ")
        try:
            room = await get_room_or_error(room_id)
        except ClientError as e:
            await self.handle_client_error(e)

        # Add user to users list of room
        if self.scope['user'].is_authenticated:
            await connect_user(room, self.scope['user'])

        # Add user to group so they can send/receive messages
        self.room_id = room.id
        await self.channel_layer.group_add(
            room.group_name,  # group name
            self.channel_name,  # channel name
        )

        # Let client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "username": self.scope['user'].username,
        })

        # Update # of users in room
        num_connected_users = get_num_connected_users(room)
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "connected.user.count",  # call connected_user_count
                "connected_user_count": num_connected_users,
            }
        )

    async def leave_room(self, room_id):
        '''
        when user send leave command, will be called by receive_json
        '''
        print("Public chat leave room: ")
        try:
            room = await get_room_or_error(room_id)
        except ClientError as e:
            await self.handle_client_error(e)

        # remove user from users list of room
        if self.scope['user'].is_authenticated:
            await disconnect_user(room, self.scope['user'])

        # remove the room we are in
        self.room_id = None

        # remove the group so that no message will be received
        await self.channel_layer.group_discard(
            room.group_name,  # group name
            self.channel_name,  # channel name
        )

        # Update # of users in room
        num_connected_users = get_num_connected_users(room)
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "connected.user.count",
                "connected_user_count": num_connected_users
            }
        )

    async def send_messages_payload(self, messages, new_page_number):
        print("Public chat send_messages_payload: ")
        await self.send_json({
            "messages_payload": "messages_payload",
            "messages": messages,
            "new_page_number": new_page_number
        })

    async def handle_client_error(self, e):
        '''
        when ClientError raised, will be called, send error to UI
        '''
        error = {}
        error['error'] = e.code
        error['message'] = e.message
        await self.send_json(error)

    async def display_progress_bar(self, is_displayed):
        '''
        is_displayed: display progress bar on UI
        not is_displayed: hide progress bar on UI
        '''
        await self.send_json({
            "display_progress_bar": is_displayed
        })

    async def connected_user_count(self, event):
        '''
        called to send # of connected users in current room
        it will show on the top of chat window
        '''
        await self.send_json({
            'msg_type': MSG_TYPE_USERS_COUNT,
            'connected_user_count': event['connected_user_count']
        })


@database_sync_to_async
def connect_user(room, user):
    return room.connect_user(user)


@database_sync_to_async
def disconnect_user(room, user):
    return room.disconnect_user(user)


@database_sync_to_async
def get_room_or_error(room_id):
    '''
    try to fetch room for user
    '''
    try:
        room = PublicChatRoom.objects.get(id=room_id)
    except PublicChatRoom.DoesNotExist:
        raise ClientError(422, "Invalid Room")
    return room


@database_sync_to_async
def save_public_room_chat_message(room, user, message):
    return PublicChatMessage.objects.create(user=user, room=room, message=message)


def get_num_connected_users(room):
    if room.users:
        return room.users.count()
    else:
        return 0


@database_sync_to_async
def get_room_chat_messages(room, page_number):
    try:
        qs = PublicChatMessage.objects.by_room(room)
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









