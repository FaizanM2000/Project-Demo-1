from django.apps import AppConfig


class PaymentConfig(AppConfig):
    name = 'tutordudes.payment'

    def ready(self):
        try:
            import tutordudes.payment.signals  # noqa F401
        except ImportError:
            pass
