DEFAULT_NOTIFICATION_PAGE_SIZE = 2

"""
"General" notifications include:
	1. FriendRequest
	2. FriendList
"""
GENERAL_MSG_TYPE_NOTIFICATIONS_PAYLOAD = 0  # New 'general' notifications data payload incoming
GENERAL_MSG_TYPE_PAGINATION_EXHAUSTED = 1  # No more 'general' notifications to retrieve
GENERAL_MSG_TYPE_NOTIFICATIONS_REFRESH_PAYLOAD = 2  # Retrieved all 'general' notifications newer than the oldest visible on screen
GENERAL_MSG_TYPE_GET_NEW_GENERAL_NOTIFICATIONS = 3  # Get any new notifications
GENERAL_MSG_TYPE_GET_UNREAD_NOTIFICATIONS_COUNT = 4  # Get unread notifications
GENERAL_MSG_TYPE_UPDATED_NOTIFICATION = 5  # Update a notifications that has been altered (Ex: Accept/decline a friend request)

"""
"Chat" notifications include:
	1. UnreadChatRoomMessages
"""
CHAT_MSG_TYPE_NOTIFICATIONS = 10  # New 'chat' notifications data payload incoming
CHAT_MSG_TYPE_PAGINATION_EXHAUSTED = 11  # notifications data payload exhuasted
CHAT_MSG_TYPE_NEW_NOTIFICATIONS = 13  # Update New 'chat' notifications data payload incoming
CHAT_MSG_TYPE_UNREAD_NOTIFICATIONS_COUNT = 14  # Get the counting of unread messages

from django.core.serializers.python import Serializer
from django.contrib.humanize.templatetags.humanize import naturaltime


class LazyNotificationEncoder(Serializer):
	"""
	Serialize a Notification into JSON.
	There are 3 types
		1. FriendRequest
		2. FriendList
		3. UnreadChatRoomMessage
	"""
	def get_dump_object(self, obj):
		dump_object = {}
		if obj.get_content_object_type() == "FriendRequest":
			dump_object.update({'notification_type': obj.get_content_object_type()})
			dump_object.update({'notification_id': str(obj.pk)})
			dump_object.update({'verb': obj.verb})
			dump_object.update({'is_active': str(obj.content_object.is_active)})
			dump_object.update({'is_read': str(obj.read)})
			dump_object.update({'natural_timestamp': str(naturaltime(obj.timestamp))})
			dump_object.update({'timestamp': str(obj.timestamp)})
			dump_object.update({
				'actions': {
					'redirect_url': str(obj.redirect_url),
				},
				"from": {
					"image_url": str(obj.from_user.profile_image.url)
				}
			})

		if obj.get_content_object_type() == "FriendList":
			dump_object.update({'notification_type': obj.get_content_object_type()})
			dump_object.update({'notification_id': str(obj.pk)})
			dump_object.update({'verb': obj.verb})
			dump_object.update({'natural_timestamp': str(naturaltime(obj.timestamp))})
			dump_object.update({'is_read': str(obj.read)})
			dump_object.update({'timestamp': str(obj.timestamp)})
			dump_object.update({
				'actions': {
					'redirect_url': str(obj.redirect_url),
				},
				"from": {
					"image_url": str(obj.from_user.profile_image.url)
				}
			})

		if obj.get_content_object_type() == "UnreadChatMessage":
			dump_object.update({'notification_type': obj.get_content_object_type()})
			dump_object.update({'notification_id': str(obj.pk)})
			dump_object.update({'verb': obj.verb})
			dump_object.update({'natural_timestamp': str(naturaltime(obj.timestamp))})
			dump_object.update({'timestamp': str(obj.timestamp)})
			dump_object.update({
				'actions': {
					'redirect_url': str(obj.redirect_url),
				},
				"from": {
					"title": str(obj.content_object.get_other_user.username),
					"image_url": str(obj.content_object.get_other_user.profile_image.url)
				}
			})

		return dump_object
