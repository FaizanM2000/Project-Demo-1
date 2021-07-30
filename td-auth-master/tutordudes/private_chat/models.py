from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from tutordudes.notification.models import Notification


class PrivateChatRoom(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user2')
    is_active = models.BooleanField(default=True)
    connected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='connected_users', null=True)

    def connect_user(self, user):
        """
        return true if user is added to the connected_users list
        """
        is_user_added = False
        if not user in self.connected_users.all():
            self.connected_users.add(user)
            is_user_added = True
        return is_user_added

    def disconnect_user(self, user):
        """
        return true if user is removed from connected_users list
        """
        is_user_removed = False
        if user in self.connected_users.all():
            self.connected_users.remove(user)
            is_user_removed = True
        return is_user_removed



    def __str__(self):
        return "Private chat between {} and {}".format(self.user1.username, self.user2.username)

    @property
    def group_name(self):
        return "PrivateChatRoom-{}".format(self.id)


class PrivateChatMessageManager(models.Manager):
    def by_room(self, room):
        qs = PrivateChatMessage.objects.filter(room=room).order_by("-timestamp")
        return qs


class PrivateChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField(unique=False, blank=False)

    objects = PrivateChatMessageManager()

    def __str__(self):
        return self.message


class UnreadChatMessage(models.Model):
    '''
    keep track of unread messages for specific user in specific private chat
    when user connected, messages will set to be "read", "count" = 0
    '''
    room = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE, related_name='room')  # room that notifications belong to
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # user that send notifications
    count = models.IntegerField(default=0)
    most_recent_message = models.CharField(max_length=255, blank=True, null=True)  # most recent message content
    reset_timestamp = models.DateTimeField()  # timestamp of first unread message
    notifications = GenericRelation(Notification)

    def __str__(self):
        return f"Messages that {str(self.user.username)} unread"

    def save(self, *args, **kwargs):
        if not self.id:  # if created, add timestamp; otherwise no change on timestamp
            self.reset_timestamp = timezone.now()
        return super(UnreadChatMessage, self).save(*args, **kwargs)

    @property
    def get_cname(self):
        return "UnreadChatMessage"

    @property
    def get_other_user(self):
        if self.user == self.room.user1:
            return self.room.user2
        else:
            return self.room.user1


@receiver(post_save, sender=PrivateChatRoom)
def create_unread_chat_messages(sender, instance, created, **kwargs):
    if created:
        unread_msg1 = UnreadChatMessage(room=instance, user=instance.user1)
        unread_msg1.save()
        unread_msg2 = UnreadChatMessage(room=instance, user=instance.user2)
        unread_msg2.save()


@receiver(pre_save, sender=UnreadChatMessage)
def incr_unread_messages_count(sender, instance, **kwargs):
    '''
    when unread message count increases, update notifications
    if no unread messages, create one
    '''
    if instance.id:
        previous = UnreadChatMessage.objects.get(id=instance.id)
        if previous.count < instance.count:
            content_type = ContentType.objects.get_for_model(instance)
            if instance.user == instance.room.user1:
                other_user = instance.room.user2
            else:
                other_user = instance.room.user1

            try:
                notification = Notification.objects.get(target=instance.user, content_type=content_type, object_id=instance.id)
                notification.verb = instance.most_recent_message
                notification.timestamp = timezone.now()
                notification.save()
            except Notification.DoesNotExist:
                instance.notifications.create(
                    target=instance.user,
                    from_user=other_user,
                    redirect_url=f"{settings.DOMAIN}/private_chat/?room_id={instance.room.id}",
                    verb=instance.most_recent_message,
                    content_type=content_type
                )


@receiver(pre_save, sender=UnreadChatMessage)
def remove_unread_msg_count(sender, instance, **kwargs):
    '''
    if unread message count decrease -> user joined chat -> delete notifications
    '''
    if instance.id:
        previous = UnreadChatMessage.objects.get(id=instance.id)
        if previous.count > instance.count:
            content_type = ContentType.objects.get_for_model(instance)
            try:
                notification = Notification.objects.get(target=instance.user, content_type=content_type, object_id=instance.id)
                notification.delete()
            except Notification.DoesNotExist:
                pass
