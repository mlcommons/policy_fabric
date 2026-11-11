"""What a requester needs before using an asset, and getting what can be got.

``assess`` builds the checklist (``app.checklist``) for an asset and the wallets
chosen for its roles; ``obtain`` then gets every credential the checklist marks
automatic -- a session key from a session-key authority, a wallet key from a
wallet key authority -- and stores it in the wallet that needs it.
"""

import logging

from . import checklist, pdo_runner, registry_client, session_keys
from .credentials import PUBLIC_KEY, WALLET_KEY, accepted, contract_id_of
from .did_utils import make_did

logger = logging.getLogger(__name__)


def _usable(user_name):
    """A session key is only worth presenting if its private half is here."""

    def usable(held):
        if held.type != PUBLIC_KEY:
            return True
        return session_keys.has_private_key(user_name, contract_id_of(held.subject), held.claims["key"])

    return usable


def assess(token_id, wallet_ids, user_name):
    """The checklist for using an asset with the wallets chosen so far.

    The asset's policy graph lists the bundles of credentials that satisfy it, its
    requirement alternatives: the full chain, say, or a credential an authority
    issued in place of part of it. The checklist is the one of the first
    alternative the requester is ready for, or else of the one that has the fewest
    credentials no accepted authority can issue, then the fewest missing.

    Returns ``{policy_id, requirements, trusted, rows, ready}``, ``requirements``
    being the chosen alternative; each row also carries the credential's display
    name.
    """
    policy_id = pdo_runner.resolve_policy_id(token_id, user_name)
    alternatives = pdo_runner.get_requirement_alternatives(token_id, user_name)
    trusted = pdo_runner.list_trusted_issuers(policy_id, user_name)
    directory = registry_client.list_authorities()
    templates = registry_client.credential_templates_by_type()
    self_asserted = {t for t, v in templates.items() if v["self_asserted"]}

    roles = sorted({role for alternative in alternatives for role in alternative})
    wallets = {
        role: (make_did(wallet_ids[role]), pdo_runner.wallet_credentials(wallet_ids[role], user_name))
        if role in wallet_ids else None
        for role in roles
    }
    assessed = []
    for alternative in alternatives:
        rows = checklist.checklist(
            alternative, trusted, {role: wallets[role] for role in alternative}, directory,
            _usable(user_name), self_asserted,
        )
        assessed.append((alternative, rows))
    requirements, rows = min(assessed, key=lambda a: (
        sum(1 for row in a[1] if row["status"] == checklist.UNREACHABLE),
        sum(1 for row in a[1] if row["status"] not in checklist.READY),
    ))
    for row in rows:
        row["name"] = templates[row["type"]]["display_name"]

    return {
        "policy_id": policy_id,
        "requirements": requirements,
        "trusted": trusted,
        "rows": rows,
        "ready": checklist.ready(rows),
    }


def _bind_session_key(authority_id, wallet_id, user_name):
    key_dir = session_keys.new_key_dir(user_name, wallet_id)
    try:
        pdo_runner.bind_session_key(authority_id, wallet_id, user_name, key_dir)
    except Exception:
        session_keys.discard(key_dir)
        raise
    return session_keys.keep(user_name, wallet_id, key_dir)


def obtain(rows, wallet_ids, user_name):
    """Get every credential the checklist marks automatic, from the system
    authority it names, into the wallet it is for. Returns what was obtained, as
    ``["<credential> from <authority>", ...]``."""
    obtained = []
    for row in rows:
        if row["status"] != checklist.AUTOMATIC:
            continue
        authority = row["via"]
        authority_id = contract_id_of(authority["did"])
        wallet_id = wallet_ids[row["role"]]

        if row["type"] == PUBLIC_KEY:
            _bind_session_key(authority_id, wallet_id, user_name)
        elif row["type"] == WALLET_KEY:
            pdo_runner.obtain_wallet_key_credential(authority_id, wallet_id, user_name)
        else:
            raise ValueError(f"{authority['name']} issues no {row['type']} on the way")
        obtained.append(f"{row['name']} from {authority['name']}")
    return obtained


def channel_key(wallet_id, trusted_issuers, user_name):
    """The key of a session key bound to the wallet by an authority the asset
    trusts, whose private half is here; ``None`` if there is none."""
    usable = _usable(user_name)
    for held in pdo_runner.wallet_credentials(wallet_id, user_name):
        if (
            held.type == PUBLIC_KEY
            and held.is_about(make_did(wallet_id))
            and accepted(held, trusted_issuers)
            and usable(held)
        ):
            return held.claims["key"]
    return None


def describe_blockers(rows):
    """Why a requester is not ready, for an error message."""
    parts = []
    for row in rows:
        if row["status"] in checklist.READY:
            continue
        who = ", ".join(row["authorities"]) or "no accepted authority"
        if row["self_asserted"]:
            parts.append(f"{row['name']}: sign it with your own wallet")
        elif row["status"] == checklist.ASK:
            parts.append(f"{row['name']}: ask {who}")
        elif row["status"] == checklist.HELD_NOT_ACCEPTED:
            parts.append(f"{row['name']}: held, but this asset accepts only {who}")
        else:
            parts.append(f"{row['name']}: no accepted authority can issue it")
    return "; ".join(parts)
