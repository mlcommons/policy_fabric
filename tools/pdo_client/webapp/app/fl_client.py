"""HTTP client for the mock FL server (``tools/fl_server``).

Every call takes the server's base URL rather than reading one from settings: an
FL server is a thing a requester chooses, not a property of this deployment.
``settings.FL_SERVER_URL`` is only the address the Federated page offers first.

Used server-side by the federated flow, for three things: reading which FL
client holds which asset DID (the server's DID -> client mapping), submitting a
round to it, and waiting for the round to come back.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = ("complete", "failed")


def default_server_url():
    return settings.FL_SERVER_URL


def normalize_url(url):
    """Clean up a hand-typed FL server address, or raise ``ValueError``."""
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValueError("an FL server URL is required")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def _url(server_url, path):
    return f"{normalize_url(server_url)}{path}"


def info(server_url, *, timeout=10):
    """Return the server's ``/info``. Raises if it is not answering."""
    resp = requests.get(_url(server_url, "/info"), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def list_clients(server_url, *, timeout=10):
    """Return the FL clients this server knows, one per asset DID.

    Each entry is one row of the server's DID -> client mapping: the
    ``client_id`` a client joined under, the ``asset_did`` it announced, and
    whether it is ``online``. The DID is what lets the caller resolve each one
    through the asset registry and show a requester what is actually available
    to run against.
    """
    resp = requests.get(_url(server_url, "/clients"), timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("clients") or []


def connected_sites(server_url, *, timeout=10):
    """The server's DID -> client mapping, connected clients only.

    Returns ``{asset_did: client}``. An asset whose DID is missing has no FL
    client that could run anything over it now, however healthy its guardian.
    """
    return {
        client["asset_did"]: client
        for client in list_clients(server_url, timeout=timeout)
        if client.get("online") and client.get("asset_did")
    }


def submit_round(server_url, script, participants, *, script_name=None, round_name=None):
    """Submit one federated round. Returns the round record.

    ``participants`` is a list of ``{"asset_did", "capability"}``: one capability
    per site, each minted by that site's own policy. The server does the
    disseminating — it matches each capability, by its DID, to the FL client
    holding that DID and addresses the job to that client alone — which is the
    only reason the DID has to travel with it. The record it returns names the
    ``client_id`` each site was matched to.
    """
    payload = {
        "script": script,
        "script_name": script_name,
        "round_name": round_name,
        "participants": participants,
    }
    resp = requests.post(_url(server_url, "/rounds"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_round(server_url, round_id, *, timeout=30):
    """Return a round's current record: per-site status, metrics, aggregate."""
    resp = requests.get(_url(server_url, f"/rounds/{round_id}"), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# There is deliberately no wait_for_round here. A round is waited out by the
# federated flow itself (``app.views.federated``), which polls so that it can
# report each site as that site reports — a helper that blocked until the whole
# round was done would hide the only part of the wait worth watching.
