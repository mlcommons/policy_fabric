import json
import logging
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic.base import View

from ..models import AppConfig

logger = logging.getLogger(__name__)


class ConfiguredRequiredMixin:
    """Mixin that redirects to /config/ if the app has not been configured yet.

    Mixin into class-based views so that page handlers don't have to repeat
    the configuration check. Place this BEFORE View in the MRO.
    """

    def dispatch(self, request, *args, **kwargs):
        if not AppConfig.get_instance().is_configured():
            return redirect("/config/")
        return super().dispatch(request, *args, **kwargs)


class BaseView(ConfiguredRequiredMixin, View):
    """Convenience base for app pages that require configuration."""

    pass


def redirect_with_msg(url, msg, msg_type="info"):
    """Redirect to ``url`` with ``?msg=...&msg_type=...`` appended.

    The base template's flash.js reads these params on page load, shows the
    message via ``alert(...)``, then strips them from the URL via
    ``history.replaceState`` so a refresh doesn't repeat them.
    """
    sep = "&" if "?" in url else "?"
    return redirect(f"{url}{sep}{urlencode({'msg': msg, 'msg_type': msg_type})}")


class ValidationError(Exception):
    """Raised by JSON endpoints when the *client* payload is bad.

    Distinct from any exception raised by PDO/contract code so JsonView can
    map only this to 400 and treat everything else as 500.
    """


class JsonView(BaseView):
    """Base for POST-only JSON endpoints.

    Subclasses implement ``handle(request, data, **kwargs)`` and return a
    JSON-serializable dict (or ``None`` for ``{"ok": true}``). Raise
    ``ValidationError`` for client-side input problems (→ 400); any other
    exception becomes a 500 with the message in ``{"error": ...}``.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        if request.body:
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"invalid JSON body: {e}"}, status=400)
        else:
            data = {}

        try:
            result = self.handle(request, data, *args, **kwargs)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("JSON endpoint %s failed", self.__class__.__name__)
            return JsonResponse({"error": str(e)}, status=500)

        if result is None:
            return JsonResponse({"ok": True})
        return JsonResponse(result)

    def handle(self, request, data, **kwargs):
        raise NotImplementedError


def require(data, *keys):
    """Pull required fields from a JSON payload, raising ValidationError if missing."""
    out = []
    for k in keys:
        v = data.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValidationError(f"missing required field: {k!r}")
        out.append(v.strip() if isinstance(v, str) else v)
    return out[0] if len(out) == 1 else tuple(out)
