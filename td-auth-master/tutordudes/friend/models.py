from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

from tutordudes.private_chat.utils import get_or_create_private_chat_room
from tutordudes.notification.models import Notification


class FriendList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="friends")

    # set up the reverse relation to GenericForeignKey
    notifications = GenericRelation(Notification)

    def __str__(self):
        return self.user.username

    def add_friend(self, users):
        """
		Add a new friend.
		"""
        if not users in self.friends.all():
            self.friends.add(users)
            self.save()

            content_type = ContentType.objects.get_for_model(self)

            # Create notifications
            # Can create this way if you want. Doesn't matter.
            Notification(
            	target=self.user,
            	from_user=users,
            	redirect_url=f"{settings.DOMAIN}/users/{users.pk}/",
            	verb=f"You are now friends with {users.username}.",
            	content_type=content_type,
            	object_id=self.id,
            ).save()

            self.notifications.create(
                target=self.user,
                from_user=users,
                redirect_url=f"{settings.DOMAIN}/users/{users.pk}/",
                verb="You are now friends with {}.".format(users.username),
                content_type=content_type,
            )
            self.save()

            # Create a private chat (or activate an old one)
            chat = get_or_create_private_chat_room(self.user, users)
            if not chat.is_active:
                chat.is_active = True
                chat.save()

    def remove_friend(self, users):
        """
		Remove a friend.
		"""
        if users in self.friends.all():
            self.friends.remove(users)

            # Deactivate the private chat between these two users
            chat = get_or_create_private_chat_room(self.user, users)
            if chat.is_active:
                chat.is_active = False
                chat.save()

    def unfriend(self, removee):
        """
		Initiate the action of unfriending someone.
		"""
        remover_friends_list = self  # person terminating the friendship

        # Remove friend from remover friend list
        remover_friends_list.remove_friend(removee)

        # Remove friend from removee friend list
        friends_list = FriendList.objects.get(user=removee)
        friends_list.remove_friend(remover_friends_list.user)

        content_type = ContentType.objects.get_for_model(self)

        # Create notifications for removee
        friends_list.notifications.create(
            target=removee,
            from_user=self.user,
            redirect_url="{}/users/{}/".format(settings.DOMAIN, self.user.pk),
            verb="You are no longer friends with {}.".format(self.user.username),
            content_type=content_type,
        )

        # Create notifications for remover
        self.notifications.create(
            target=self.user,
            from_user=removee,
            redirect_url="{}/users/{}/".format(settings.DOMAIN, removee.pk),
            verb="You are no longer friends with {}.".format(removee.username),
            content_type=content_type,
        )

    @property
    def get_cname(self):
        """
		For determining what kind of object is associated with a Notification
		"""
        return "FriendList"

    def is_mutual_friend(self, friend):
        """
		Is this a friend?
		"""
        if friend in self.friends.all():
            return True
        return False


class FriendRequest(models.Model):
    """
	A friend request consists of two main parts:
		1. SENDER
			- Person sending/initiating the friend request
		2. RECIVER
			- Person receiving the friend friend
	"""

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sender")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receiver")

    is_active = models.BooleanField(blank=False, null=False, default=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    notifications = GenericRelation(Notification)

    def __str__(self):
        return self.sender.username

    def accept(self):
        """
		Accept a friend request.
		Update both SENDER and RECEIVER friend lists.
		"""
        receiver_friend_list = FriendList.objects.get(user=self.receiver)
        if receiver_friend_list:
            content_type = ContentType.objects.get_for_model(self)

            # Update notifications for RECEIVER
            receiver_notification = Notification.objects.get(target=self.receiver, content_type=content_type,
                                                             object_id=self.id)
            receiver_notification.is_active = False
            receiver_notification.redirect_url = "{}/users/{}/".format(settings.DOMAIN, self.sender.id)
            receiver_notification.verb = "You accepted {}'s friend request.".format(self.sender.username)
            receiver_notification.timestamp = timezone.now()
            receiver_notification.save()

            receiver_friend_list.add_friend(self.sender)

            sender_friend_list = FriendList.objects.get(user=self.sender)
            if sender_friend_list:
                # Create notifications for SENDER
                self.notifications.create(
                    target=self.sender,
                    from_user=self.receiver,
                    redirect_url=f"{settings.DOMAIN}/users/{self.receiver.pk}/",
                    verb=f"{self.receiver.username} accepted your friend request.",
                    content_type=content_type,
                )

                sender_friend_list.add_friend(self.receiver)
                # sender_friend_list.save()
                self.is_active = False
                self.save()
            return receiver_notification  # we will need this later to update the realtime notifications

    def decline(self):
        """
		Decline a friend request.
		Is it "declined" by setting the `is_active` field to False
		"""
        self.is_active = False
        self.save()

        content_type = ContentType.objects.get_for_model(self)

        # Update notifications for RECEIVER
        notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
        notification.is_active = False
        notification.redirect_url = f"{settings.DOMAIN}/users/{self.sender.pk}/"
        notification.verb = f"You declined {self.sender}'s friend request."
        notification.from_user = self.sender
        notification.timestamp = timezone.now()
        notification.save()

        # Create notifications for SENDER
        self.notifications.create(
            target=self.sender,
            verb=f"{self.receiver.username} declined your friend request.",
            from_user=self.receiver,
            redirect_url=f"{settings.DOMAIN}/users/{self.receiver.pk}/",
            content_type=content_type,
        )

        return notification

    def cancel(self):
        """
		Cancel a friend request.
		Is it "cancelled" by setting the `is_active` field to False.
		This is only different with respect to "declining" through the notifications that is generated.
		"""
        self.is_active = False
        self.save()

        content_type = ContentType.objects.get_for_model(self)

        # Create notifications for SENDER
        self.notifications.create(
            target=self.sender,
            verb=f"You cancelled the friend request to {self.receiver.username}.",
            from_user=self.receiver,
            redirect_url=f"{settings.DOMAIN}/users/{self.receiver.pk}/",
            content_type=content_type,
        )

        notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
        notification.verb = f"{self.sender.username} cancelled the friend request sent to you."
        # notifications.timestamp = timezone.now()
        notification.read = False
        notification.save()

    @property
    def get_cname(self):
        """
		For determining what kind of object is associated with a Notification
		"""
        return "FriendRequest"


@receiver(post_save, sender=FriendRequest)
def create_notification(sender, instance, created, **kwargs):
    if created:
        instance.notifications.create(
            target=instance.receiver,
            from_user=instance.sender,
            redirect_url=f"{settings.DOMAIN}/users/{instance.sender.pk}/",
            verb=f"{instance.sender.username} sent you a friend request.",
            content_type=instance,
        )
