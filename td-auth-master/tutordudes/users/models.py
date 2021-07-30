from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.db.models import ImageField
from taggit.managers import TaggableManager

class User(AbstractUser):
    profile_image = ImageField(null=True, blank=True, upload_to='profile_pics/', default='default_image.png')
    stripe_customer_id = CharField(max_length=50, null=True, blank=True)
    tags = TaggableManager(blank=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

    def get_profile_name(self):
        return self.username

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})
