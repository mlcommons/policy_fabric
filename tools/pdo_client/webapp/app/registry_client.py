"""
HTTP client for asset_registry and template_registry.
Used server-side by Django views via the requests library.
"""

import requests
from django.conf import settings


# ============================================================
# Asset Registry
# ============================================================


def list_assets():
    """Fetch all assets from the asset registry. Returns a list of dicts."""
    url = f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def register_asset(name, did, metadata=None):
    """Register a new asset in the asset registry. Returns the created asset dict."""
    url = f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/"
    payload = {"name": name, "did": did, "metadata": metadata or {}}
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_asset(pk):
    """Get a single asset by pk from the asset registry."""
    url = f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{pk}/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_asset_by_did(did):
    """Find an asset by exact DID. Returns asset dict or raises requests.HTTPError."""
    url = f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/by_did/"
    resp = requests.get(url, params={"did": did}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_asset_metadata(pk, metadata_updates):
    """Merge metadata_updates into an existing asset's metadata (by registry pk)."""
    url = f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{pk}/"
    resp = requests.patch(url, json={"metadata": metadata_updates}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_asset_metadata_by_did(did, metadata_updates):
    """Find an asset by DID and merge metadata_updates into its metadata."""
    asset = get_asset_by_did(did)
    return update_asset_metadata(asset["id"], metadata_updates)


# ============================================================
# Template Registry
# ============================================================


def list_policy_templates():
    """Fetch all policy templates from the template registry."""
    url = f"{settings.TEMPLATE_REGISTRY_URL.rstrip('/')}/api/policies/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_policy_template(pk):
    """Get a single policy template by pk."""
    url = f"{settings.TEMPLATE_REGISTRY_URL.rstrip('/')}/api/policies/{pk}/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_credential_templates():
    """Fetch all credential templates from the template registry."""
    url = f"{settings.TEMPLATE_REGISTRY_URL.rstrip('/')}/api/credentials/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_credential_template(pk):
    """Get a single credential template by pk."""
    url = f"{settings.TEMPLATE_REGISTRY_URL.rstrip('/')}/api/credentials/{pk}/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()
