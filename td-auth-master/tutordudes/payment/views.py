import json
import stripe
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.conf import settings
from django.views.generic import TemplateView
from .models import Pricing, Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


def get_publishable_key(request):
    return JsonResponse({
        'publishableKey': settings.STRIPE_PUBLIC_KEY,
        'bronzePrice': settings.BRONZE_PRICE_ID,
        'goldPrice': settings.GOLD_PRICE_ID,
        'silverPrice': settings.SILVER_PRICE_ID,
    })


class SubscriptionView(TemplateView):
    template_name = 'payment/subscriptions.html'


def payment_success(request):
    print("session_id: " + request.GET['session_id'])
    session = stripe.checkout.Session.retrieve(request.GET['session_id'])
    # print(session)
    # customer = stripe.Customer.retrieve(session.customer)
    # context = {
    #     'session': session,
    #     'session': session,
    #     'customer': customer
    # }
    # print(session)
    # print(customer)
    return render(request, 'payment/success.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')


class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        domain_url = settings.DOMAIN

        try:
            # Create new Checkout Session for the order
            # Other optional params include:
            # [billing_address_collection] - to display billing address details on the page
            # [customer] - if you have an existing Stripe Customer ID
            # [customer_email] - lets you prefill the email input in the form
            # For full details see https:#stripe.com/docs/api/checkout/sessions/create

            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url +
                            "/payment/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/payment/canceled",
                payment_method_types=["card"],
                customer=request.user.stripe_customer_id,
                mode="subscription",
                line_items=[
                    {
                        "price": data['priceId'],
                        "quantity": 1
                    }
                ],
            )
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            print(str(e))
            return JsonResponse({'error': {'message': str(e)}})


class CustomerPortalView(View):
    def post(self, request, *args, **kwargs):
        session = stripe.billing_portal.Session.create(
            customer=request.user.stripe_customer_id,
            return_url=settings.DOMAIN,
        )

        return JsonResponse({'url': session.url})


# send post request without csrf token to this view
@csrf_exempt
def webhook(request):
    # You can use webhooks to receive information about asynchronous payment events.
    # For more about our webhook events check out https://stripe.com/docs/webhooks.
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body

    # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
    signature = request.META["HTTP_STRIPE_SIGNATURE"]
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=signature, secret=webhook_secret)
        data = event['data']

    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Get the type of webhook event sent - used to check the status of PaymentIntents.
    event_type = event['type']

    if event_type == 'invoice.paid':
        # Used to provision services after the trial has ended.
        # The status of the invoice will show up as paid. Store the status in your
        # database to reference when a user accesses your service to avoid hitting rate
        # limits.
        # change the users subscription and pricing
        print(data)

        webhook_object = data["object"]
        stripe_customer_id = webhook_object["customer"]
        stripe_sub = webhook_object["lines"]["data"][0]
        stripe_price_id = stripe_sub["price"]["id"]
        pricing = Pricing.objects.get(stripe_price_id=stripe_price_id)

        stripe_subscription_id = webhook_object["subscription"]
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
        subscription_status = stripe_sub['status']

        # 通过stripe API获取当前用户正在使用的subscription id，然后通过subscription id获取对应的pricing id
        # 然后更新用户当前关联的subscription和subscription关联的pricing
        user = User.objects.get(stripe_customer_id=stripe_customer_id)
        user.subscription.status = subscription_status
        user.subscription.stripe_subscription_id = stripe_subscription_id
        user.subscription.pricing = pricing
        user.subscription.save()

    if event_type == 'invoice.finalized':
        # If you want to manually send out invoices to your customers
        # or store them locally to reference to avoid hitting Stripe rate limits.
        print(data)

    if event_type == 'customer.subscription.deleted':
        # handle subscription cancelled automatically based
        # upon your subscription settings. Or if the user cancels it.
        webhook_object = data["object"]
        stripe_customer_id = webhook_object["customer"]

        # 当用户delete substription时，只需要从stripe获取当前substription的status，更新本地user关联的subscription的status即可
        stripe_sub = stripe.Subscription.retrieve(webhook_object["id"])
        user = User.objects.get(stripe_customer_id=stripe_customer_id)
        user.subscription.status = stripe_sub["status"]
        user.subscription.save()

    if event_type == 'customer.subscription.trial_will_end':
        # Send notifications to your user that the trial will end
        print(data)

    if event_type == 'customer.subscription.updated':
        print(data)

    return HttpResponse()
