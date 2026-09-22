import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

from ..identity import ensure_provisioned, provision_identity, set_current_identity
from ..models import AppConfig
from ._helpers import redirect_with_msg
from ._streaming import stream_events

logger = logging.getLogger(__name__)


class ConfigPageView(View):
    """GET shows the config form; POST saves and redirects.

    Only the user identity (``public_key``) is editable. Service URLs are
    deployment configuration (Django settings, set via the environment).
    """

    template_name = "config.html"

    def get(self, request):
        return render(request, self.template_name, {"config": AppConfig.get_instance()})

    def post(self, request):
        config = AppConfig.get_instance()
        if "public_key" in request.POST:
            config.public_key = request.POST["public_key"].strip()
        config.save()
        ensure_provisioned(config.public_key)
        target = "/" if config.is_configured() else "/config/"
        return redirect_with_msg(target, "Configuration saved.", "success")


class IdentitySetView(View):
    """POST-only: change the current identity from the navbar modal.

    No-JS fallback for :class:`IdentityProvisionView`: it provisions inline
    (blocking) and redirects, rather than streaming progress.
    """

    def post(self, request):
        public_key = (request.POST.get("public_key") or "").strip()
        if not public_key:
            return redirect_with_msg("/", "public_key is required", "error")
        set_current_identity(public_key)
        # First time we see this user, give them a wallet.
        ensure_provisioned(public_key)
        # Always land on the home page after switching identity, so the view
        # reflects the newly selected user's contracts.
        return redirect_with_msg("/", f"Identity set to {public_key}.", "success")


def _read_public_key(request):
    """Pull ``public_key`` from a JSON body (provision.js) or a form POST."""
    if request.content_type == "application/json" and request.body:
        try:
            return (json.loads(request.body).get("public_key") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            return ""
    return (request.POST.get("public_key") or "").strip()


class IdentityProvisionView(View):
    """POST {public_key} — switch identity and provision it, streaming one NDJSON
    progress line per high-level step so the UI can show what happens behind the
    scenes (creating the wallet).

    Driven by ``provision.js``; :class:`IdentitySetView` and
    :class:`ConfigPageView` remain the no-JS fallbacks.
    """

    http_method_names = ["post"]

    def post(self, request):
        public_key = _read_public_key(request)
        if not public_key:
            return JsonResponse({"error": "public_key is required"}, status=400)

        # Switch the identity up front (committed before the stream starts) so
        # the page the client loads next reflects the new user.
        set_current_identity(public_key)
        return stream_events(
            provision_identity(public_key),
            complete=lambda: {"redirect": "/"},
        )
