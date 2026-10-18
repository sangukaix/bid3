"""Small public demo limits; counters are local to this API process."""
from hashlib import sha256

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class PublicLoginThrottle(SimpleRateThrottle):
    scope = "public_login"
    rate = "8/min"

    def get_cache_key(self, request, view):
        if not settings.BID3_PUBLIC_WEB:
            return None
        username = str(request.data.get("username", "")).strip().casefold()
        return self.cache_format % {"scope": self.scope, "ident": sha256(username.encode()).hexdigest()}


class PublicLoginGlobalThrottle(PublicLoginThrottle):
    scope = "public_login_global"
    rate = "60/min"

    def get_cache_key(self, request, view):
        if settings.BID3_PUBLIC_WEB:
            return self.cache_format % {"scope": self.scope, "ident": "all"}
        return None


class PublicSignupThrottle(PublicLoginGlobalThrottle):
    scope = "public_signup"
    rate = "10/hour"
