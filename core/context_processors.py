from django.conf import settings as django_settings
from rest_framework_api_key.models import APIKey


def global_premium_status(request):
    """
    Makes 'is_premium' available in ALL templates (Navbar, Modals, etc).
    """
    if request.user.is_authenticated:
        is_premium = APIKey.objects.filter(name=request.user.email).exists()
        return {'is_premium': is_premium}

    return {'is_premium': False}


def social_login_status(request):
    google_available = False
    try:
        providers = getattr(django_settings, 'SOCIALACCOUNT_PROVIDERS', {})
        app_cfg = providers.get('google', {}).get('APP', {})
        if app_cfg.get('client_id'):
            google_available = True
        else:
            from allauth.socialaccount.models import SocialApp
            google_available = SocialApp.objects.filter(provider='google').exists()
    except Exception:
        pass
    return {'google_login_available': google_available}