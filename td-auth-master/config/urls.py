from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from .views import ContactView

urlpatterns = [

                  path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
                  path("home/", TemplateView.as_view(template_name="pages/home.html"), name="home"),
                  path("about/", TemplateView.as_view(template_name='pages/about.html'), name="about"),
                  path("search/", TemplateView.as_view(template_name='pages/search.html'), name='search'),
                  path("results/", TemplateView.as_view(template_name='pages/results.html'), name='results'),
                  path("reviews/", TemplateView.as_view(template_name='pages/reviews.html'), name='reviews'),
                  path("careers/", TemplateView.as_view(template_name='pages/careers.html'), name='careers'),
                  path("internships/", TemplateView.as_view(template_name='pages/internships.html'),
                       name='internships'),
                  path("contact/", ContactView.as_view(), name="contact"),
                  path("privacy/", TemplateView.as_view(template_name='pages/privacy.html'), name='privacy'),

                  # Django Admin, use {% url 'admin:index' %}
                  path(settings.ADMIN_URL, admin.site.urls),

                  # User management
                  path("users/", include("tutordudes.users.urls", namespace="users")),
                  path("accounts/", include("allauth.urls")),
                  # Your stuff: custom urls includes go here
                  path('payment/', include("tutordudes.payment.urls", namespace="payment")),
                  path("friend/", include('tutordudes.friend.urls', namespace='friend')),

                  path("public_chat/", include("tutordudes.public_chat.urls", namespace='public_chat')),
                  path("private_chat/", include("tutordudes.private_chat.urls", namespace='private_chat')),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
