# jobs/throttles.py

from rest_framework.throttling import SimpleRateThrottle
from rest_framework_api_key.models import APIKey
from django.contrib.auth import get_user_model

User = get_user_model()

class FreeTierThrottle(SimpleRateThrottle):
    scope = 'free_tier'
    rate = '20/day'

    def get_cache_key(self, request, view):
        # 1. Check if it's a Browser/HTMX request (Allow)
        # NOTE: don't use request.accepts('text/html') here — it returns True
        # for 'Accept: */*' (curl/requests default), which let every anonymous
        # API client bypass throttling entirely.
        accept_header = request.headers.get('Accept', '')
        if 'text/html' in accept_header or request.headers.get('HX-Request') == 'true':
            return None

        ident = self.get_ident(request)  # Default to IP address

        # 2. Check for API Key
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Api-Key "):
            try:
                key_value = auth_header.split()[1]
                api_key = APIKey.objects.get_from_key(key_value)
                if api_key:
                    # Get the user and their plan
                    email = api_key.name
                    user = User.objects.filter(email=email).first()
                    sub = getattr(user, 'subscription', None)

                    # If they are Pro or Business, RETURN NONE to skip this throttle
                    # (The Pro/Business throttles will handle them)
                    if sub and sub.plan_type in ['pro', 'business']:
                        return None

                    # If we are here, they are Authenticated but Free.
                    # --- CHANGE: Track by User ID, not Key ID ---
                    if user:
                        ident = user.id
                    else:
                        ident = api_key.id
            except Exception:
                pass

        # 3. Apply the 20/day limit to the identifier (IP or User ID)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

class ProTierThrottle(SimpleRateThrottle):
    """
    Limits: 1,000/day
    Applies ONLY if the user's Subscription is 'pro'
    """
    scope = 'pro_tier'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        return self.check_plan_limit(request, 'pro')

    def check_plan_limit(self, request, required_plan):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None  # Not an API request, ignore.

        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)

            if api_key:
                # Find the user by email (stored in api_key.name)
                email = api_key.name
                user = User.objects.filter(email=email).first()

                if user:
                    # Check their subscription plan
                    sub = getattr(user, 'subscription', None)
                    # If they match the plan, apply this throttle
                    if sub and sub.plan_type == required_plan:
                        # --- CHANGE: Track by User ID ---
                        return self.cache_format % {
                            'scope': self.scope,
                            'ident': user.id
                        }
        except Exception:
            pass
        return None


class BusinessTierThrottle(SimpleRateThrottle):
    """
    Limits: 10,000/day
    Applies ONLY if the user's Subscription is 'business'
    """
    scope = 'business_tier'
    rate = '10000/day'

    def get_cache_key(self, request, view):
        # Reuse logic but look for 'business' plan
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None

        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)

            if api_key:
                email = api_key.name
                user = User.objects.filter(email=email).first()

                if user:
                    sub = getattr(user, 'subscription', None)
                    if sub and sub.plan_type == 'business':
                        # --- CHANGE: Track by User ID ---
                        return self.cache_format % {
                            'scope': self.scope,
                            'ident': user.id
                        }
        except Exception:
            pass
        return None