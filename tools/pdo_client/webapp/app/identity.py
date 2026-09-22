"""
Public key / identity abstraction layer.
The current identity is the public_key field of the singleton AppConfig.
"""

import logging
import os

from django.conf import settings

from . import naming
from .did_utils import make_did
from .models import AppConfig

logger = logging.getLogger(__name__)

_KEY_SUFFIX = "_private.pem"


def get_current_identity():
    """Return the current public key (username) or empty string."""
    return AppConfig.get_instance().public_key


def list_available_identities():
    """Return the identities that have keys in USER_KEYS_FOLDER, sorted.

    PDO user keys are named ``<name>_private.pem``; the base name is the
    identity used to sign. Returns an empty list if the folder is missing.
    """
    try:
        names = [
            fname[: -len(_KEY_SUFFIX)]
            for fname in os.listdir(settings.USER_KEYS_FOLDER)
            if fname.endswith(_KEY_SUFFIX)
        ]
    except OSError:
        return []
    return sorted(names)


def set_current_identity(public_key):
    """Set the current identity (public key / username)."""
    config = AppConfig.get_instance()
    config.public_key = public_key
    config.save(update_fields=["public_key"])


# High-level provisioning steps, in order. The labels are what the UI shows
# while the work runs behind the scenes.
PROVISION_STEPS = (("wallet", "Creating your wallet"),)


def provision_identity(user_name):
    """Provision a freshly selected identity, yielding one progress event per
    high-level step so a caller can surface what happens behind the scenes.

    Ensures the user has a wallet. Idempotent and best-effort: failure is
    reported but never raised.

    Each yielded event is a dict ``{"step", "status", "label", "detail"}`` where
    ``status`` is ``start`` | ``done`` | ``skip`` | ``error``.
    """
    if not user_name:
        return

    # Imported lazily: pdo_runner pulls in the heavy pdo.* stack, and this module
    # is imported on every request (context processor).
    from . import ledger_client, pdo_runner

    labels = dict(PROVISION_STEPS)

    def event(step, status, detail=""):
        return {"step": step, "status": status, "label": labels[step], "detail": detail}

    # --- wallet -----------------------------------------------------------
    yield event("wallet", "start")
    try:
        if ledger_client.list_identity_ids(user_name):
            yield event("wallet", "skip", "already have a wallet")
        else:
            contract_id = pdo_runner.create_wallet(f"{user_name}_wallet", user_name)
            naming.set_name(make_did(contract_id), f"{user_name}_wallet")
            yield event("wallet", "done")
    except Exception as e:
        logger.exception("Failed to ensure a wallet for %s", user_name)
        yield event("wallet", "error", str(e))


def ensure_provisioned(user_name):
    """Provision a user (a wallet) if they don't have one yet.

    Called when the identity is switched so a user is ready to use without any
    manual setup. Drains ``provision_identity`` for callers that don't surface
    per-step progress. Idempotent and best-effort.
    """
    for _ in provision_identity(user_name):
        pass


def is_configured():
    return bool(get_current_identity())
