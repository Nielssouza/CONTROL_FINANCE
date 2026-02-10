from django.conf import settings


def app_flags(request):
    return {
        "app_debug": settings.DEBUG,
        "app_public_signup_enabled": getattr(settings, "PUBLIC_SIGNUP_ENABLED", False),
    }
