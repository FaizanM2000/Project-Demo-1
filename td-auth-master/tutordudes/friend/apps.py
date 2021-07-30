from django.apps import AppConfig


class FriendConfig(AppConfig):
    name = 'tutordudes.friend'

    def ready(self):
        try:
            import tutordudes.friend.signals  # noqa F401
        except ImportError:
            pass
