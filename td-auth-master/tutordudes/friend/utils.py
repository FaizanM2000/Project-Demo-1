from .models import FriendRequest


def get_friend_request(sender, receiver):
    # return friend_request or false
    try:
        return FriendRequest.objects.get(sender=sender, receiver=receiver, is_active=True)
    except FriendRequest.DoesNotExist:
        return False
