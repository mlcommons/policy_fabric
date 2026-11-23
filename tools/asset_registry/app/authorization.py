"""Bearer-only API writes; browser session cookies never authorize mutations."""
from functools import wraps
from hmac import compare_digest

from django.conf import settings
from django.http import JsonResponse


def authorize_registry_write(view):
    @wraps(view)
    def authorized(request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            expected = settings.REGISTRY_WRITE_TOKEN
            supplied = request.headers.get("Authorization", "")
            if not expected or not compare_digest(
                supplied.encode("utf-8"), ("Bearer " + expected).encode("utf-8")
            ):
                response = JsonResponse({"error": "Registry write authorization required"}, status=401)
                response["WWW-Authenticate"] = "Bearer"
                return response
        return view(request, *args, **kwargs)
    return authorized
