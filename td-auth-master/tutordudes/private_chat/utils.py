from .models import PrivateChatRoom
from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime
from datetime import datetime

MSG_TYPE_MESSAGE = 0  # standard message
MSG_TYPE_USERS_COUNT = 1  # users count message
MSG_TYPE_ENTER = 1  # user enter signal
MSG_TYPE_LEAVE = 2  # user leave signal

DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE = 10
DEFAULT_NOTIFICATION_PAGE_SIZE = 5


def get_or_create_private_chat_room(user1, user2):
    try:
        room = PrivateChatRoom.objects.get(user1=user1, user2=user2)
    except PrivateChatRoom.DoesNotExist:
        try:
            room = PrivateChatRoom.objects.get(user1=user2, user2=user1)
        except PrivateChatRoom.DoesNotExist:
            room = PrivateChatRoom.objects.create(user1=user1, user2=user2)
            room.save()

    return room


class ClientError(Exception):
    '''
    custom exception class that will be handled by websocket receive()
    then translate into a message sent back to client
    '''

    def __init__(self, code, message):
        super().__init__(code)
        self.code = code
        self.message = message


def calculate_timestamp(timestamp):
    '''
    1. Today or yesterday:
        - EX: 'today at 10:56 AM'
        - EX: 'yesterday at 5:19 PM'
    2. other:
        - EX: 05/06/2020
        - EX: 12/28/2020
    '''

    # today or yesterday
    if naturalday(timestamp) == 'today' or naturalday(timestamp) == 'yesterday':
        str_time = datetime.strftime(timestamp, "%I:%M %p")
        str_time = str_time.strip("0")
        ts = "{} at {}".format(naturalday(timestamp), str_time)
    else:
        str_time = datetime.strftime(timestamp, "%m/%d/%Y")
        ts = "{}".format(str_time)

    return ts
