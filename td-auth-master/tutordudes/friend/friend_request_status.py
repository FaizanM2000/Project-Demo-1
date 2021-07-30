from enum import Enum

'''
is_self:
    True: show your own profile (with update button)
    False:
        is_friend:
            True: show send message button
            False:
                NO_REQUEST_SENT: show send request button
                THEM_SENT_TO_YOU: show accept request button
                YOU_SENT_TO_THEM: show cancel request button
'''


class FriendRequestStatus(Enum):
    NO_REQUEST_SENT = -1
    THEM_SENT_TO_YOU = 0
    YOU_SENT_TO_THEM = 1
