from django.shortcuts import render

from .models import Event


def event_list(request):
    events = Event.objects.all().order_by('date')
    context = {
        'events': events,
        'page_title': 'Upcoming Events',
    }
    return render(request, 'events/event_list.html', context)
