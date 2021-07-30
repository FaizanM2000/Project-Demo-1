from django.db import models
from django.conf import settings


class PublicChatRoom(models.Model):
    title = models.CharField(max_length=255, unique=True, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    def __str__(self):
        return self.title

    def connect_user(self, user):
        # return True if user is added
        is_user_added = True
        if not user in self.users.all():
            self.users.add(user)
            self.save()
            is_user_added = True
        elif user in self.users.all():
            is_user_added = True
        return is_user_added

    def disconnect_user(self, user):
        # return True if user is removed
        is_user_removed = False
        if user in self.users.all():
            self.users.remove(user)
            self.save()
            is_user_removed = True
        return is_user_removed

    @property
    def group_name(self):
        # return channel group name that sockets subscribe to and get messages when they are sent
        return "PublicChatRoom-" + str(self.id)


class PublicChatMessageManager(models.Manager):
    def by_room(self, room):
        qs = PublicChatMessage.objects.filter(room=room).order_by('-timestamp')
        return qs


class PublicChatMessage(models.Model):
    # chat messages created by one user inside a PublicChatRoom (foreignKey)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(PublicChatRoom, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField(unique=False, blank=False)

    objects = PublicChatMessageManager()

    def __str__(self):
        return self.content



