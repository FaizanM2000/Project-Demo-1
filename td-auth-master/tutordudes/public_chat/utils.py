from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime
from datetime import datetime

MSG_TYPE_MESSAGE = 0  # standard message
MSG_TYPE_USERS_COUNT = 1  # users count message
DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE = 10


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
