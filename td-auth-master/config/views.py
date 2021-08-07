from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.views.generic import FormView
from .forms import ContactForm


class ContactViewNew(FormView):
    form_class = ContactForm
    template_name = 'pages/options.html'

    def get_success_url(self):
        return reverse("contact")

    def form_valid(self, form):
        messages.info(self.request, 'Thanks for getting in touch. We have received your message.')
        name = form.cleaned_data.get('name')
        email = form.cleaned_data.get('email')
        subject = form.cleaned_data.get("subject")
        message = form.cleaned_data.get('message')

        full_message = '''
        Received message from {}, {}
        ______________________________________

        {}
        '''.format(name, email, message)
        send_mail(
            subject=subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.NOTIFY_EMAIL]
        )

        return super(ContactViewNew, self).form_valid(form)

class ContactView(FormView):
    form_class = ContactForm
    template_name = 'pages/contact.html'

    def get_success_url(self):
        return reverse("contact")

    def form_valid(self, form):
        messages.info(self.request, 'Thanks for getting in touch. We have received your message.')
        name = form.cleaned_data.get('name')
        email = form.cleaned_data.get('email')
        subject = form.cleaned_data.get('subject')
        message = form.cleaned_data.get('message')

        full_message = '''
        Received message from {}, {}
        ______________________________________

        {}
        '''.format(name, email, message)
        send_mail(
            subject= subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.NOTIFY_EMAIL]
        )

        return super(ContactView, self).form_valid(form)
