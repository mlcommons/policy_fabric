import logging

from django.shortcuts import render

from .. import registry_client
from ._helpers import BaseView

logger = logging.getLogger(__name__)


class PoliciesView(BaseView):
    """GET-only: every policy card in the catalog, drawn as its graph of components.
    Read-only: cards change in the docs site's Policy Composer, through a pull request."""

    def get(self, request):
        try:
            catalog = registry_client.get_catalog()
            error = None
        except Exception as e:
            logger.exception("Failed to fetch the policy catalog")
            catalog, error = None, str(e)
        cards = []
        if catalog is not None:
            cards = sorted(
                ({"folder": folder, **card} for folder, card in catalog["cards"].items()),
                key=lambda c: (c["graph"]["root"], c["name"].lower()),
            )
        return render(request, "policies/list.html", {"catalog": catalog, "cards": cards, "error": error})
