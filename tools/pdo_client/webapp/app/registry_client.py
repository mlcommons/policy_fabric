"""
HTTP client for asset_registry and template_registry.
Used server-side by Django views via the requests library.
"""

import requests
from django.conf import settings


def _asset_registry(path):
    return f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/{path}"


def _template_registry(path):
    return f"{settings.TEMPLATE_REGISTRY_URL.rstrip('/')}/api/{path}"


def _get(url, params):
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _send(method, url, payload):
    resp = requests.request(method, url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ============================================================
# Asset Registry: assets
# ============================================================


def list_assets():
    """Fetch all assets from the asset registry. Returns a list of dicts."""
    return _get(_asset_registry("assets/"), {})


def register_asset(name, did, metadata):
    """Register a new asset in the asset registry. Returns the created asset dict."""
    return _send("POST", _asset_registry("assets/"), {"name": name, "did": did, "metadata": metadata})


def get_asset(pk):
    """Get a single asset by pk from the asset registry."""
    return _get(_asset_registry(f"assets/{pk}/"), {})


def get_asset_by_did(did):
    """Find an asset by exact DID. Returns asset dict or raises requests.HTTPError."""
    return _get(_asset_registry("assets/by_did/"), {"did": did})


def update_asset_metadata(pk, metadata_updates):
    """Merge metadata_updates into an existing asset's metadata (by registry pk)."""
    return _send("PATCH", _asset_registry(f"assets/{pk}/"), {"metadata": metadata_updates})


def update_asset_metadata_by_did(did, metadata_updates):
    """Find an asset by DID and merge metadata_updates into its metadata."""
    asset = get_asset_by_did(did)
    return update_asset_metadata(asset["id"], metadata_updates)


# ============================================================
# Asset Registry: the directory of authorities and trust lists
# ============================================================


def list_authorities():
    """Every directory entry."""
    return _get(_asset_registry("authorities/"), {})


def register_authority(record):
    return _send("POST", _asset_registry("authorities/"), record)


def update_authority(pk, changes):
    return _send("PATCH", _asset_registry(f"authorities/{pk}/"), changes)


def get_authority_by_did(did):
    return _get(_asset_registry("authorities/by_did/"), {"did": did})


def list_trust_lists():
    return _get(_asset_registry("trust_lists/"), {})


# ============================================================
# Template Registry
# ============================================================


def list_policy_templates():
    """Every policy and delivery template."""
    return _get(_template_registry("policies/"), {})


def policy_templates_for(guardian_type, kind):
    """The templates of a kind (``policy`` or ``delivery``) for a guardian type."""
    return _get(_template_registry("policies/"), {"guardian_type": guardian_type, "kind": kind})


def get_policy_template(pk):
    """Get a single policy template by pk."""
    return _get(_template_registry(f"policies/{pk}/"), {})


def delivery_template(guardian_type):
    """The delivery module of a guardian type."""
    modules = policy_templates_for(guardian_type, "delivery")
    if len(modules) != 1:
        raise ValueError(f"expected one delivery module for {guardian_type!r}, found {len(modules)}")
    return modules[0]


def list_authority_templates():
    """Every rule-based authority card."""
    return _get(_template_registry("authorities/"), {})


def get_authority_template(pk):
    return _get(_template_registry(f"authorities/{pk}/"), {})


def list_credential_templates():
    """Fetch all credential templates from the template registry."""
    return _get(_template_registry("credentials/"), {})


def credential_templates_by_type():
    return {t["template_type"]: t for t in list_credential_templates()}


def get_credential_template(pk):
    """Get a single credential template by pk."""
    return _get(_template_registry(f"credentials/{pk}/"), {})
