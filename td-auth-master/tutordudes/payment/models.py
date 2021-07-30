from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
import stripe

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class Pricing(models.Model):
    name = models.CharField(max_length=100) # Free Trial, Bronze, Silver, Gold
    slug = models.SlugField()
    stripe_price_id = models.CharField(max_length=50, default='')
    price = models.DecimalField(decimal_places=2, max_digits=5, default=19)
    currency = models.CharField(max_length=50, default='usd')

    def __str__(self):
        return self.name


# one user -> one Subscription -> one pricing
# one pricing -> many Subscription with same charge -> many user
class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, related_name='subscription')
    pricing = models.ForeignKey(Pricing, on_delete=models.CASCADE, related_name='subscriptions')
    created_at = models.DateTimeField(auto_now_add=True)

    # should be got from stripe
    status = models.CharField(max_length=100)
    stripe_subscription_id = models.CharField(max_length=50)

    def __str__(self):
        return self.user.email


def post_save_user(sender, instance, created, **kwargs):
    if created:
        free_trial = Pricing.objects.get(name='Free Trial')
        subscription = Subscription.objects.create(user=instance, pricing=free_trial)

        stripe_customer = stripe.Customer.create(
            email=instance.email
        )
        stripe_subscription = stripe.Subscription.create(
            customer=stripe_customer["id"],
            items=[{'price': settings.FREE_TRIAL_ID}],
            trial_period_days=3
        )

        # print(stripe_subscription)
        subscription.status = stripe_subscription["status"]  # trialing
        subscription.stripe_subscription_id = stripe_subscription["id"]
        subscription.save()

        instance.stripe_customer_id = stripe_customer["id"]
        instance.save()


def user_logged_in_receiver(sender, user, **kwargs):
    subscription = user.subscription
    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
    subscription.status = stripe_subscription['status']
    subscription.save()


post_save.connect(post_save_user, sender=User)
user_logged_in.connect(user_logged_in_receiver)
