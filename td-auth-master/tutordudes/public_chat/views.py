from django.shortcuts import render

from django.shortcuts import render
from django.conf import settings


def home(request):
    context = {}
    context['debug_mode'] = settings.DEBUG
    context['room_id'] = 1
    return render(request, 'chat/home.html', context=context)
