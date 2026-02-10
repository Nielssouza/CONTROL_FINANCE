from django.conf import settings


def app_flags(request):
    return {
        "app_debug": settings.DEBUG,
    }
