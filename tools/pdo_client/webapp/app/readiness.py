"""What a requester needs before using an asset, and getting what can be got.

``assess`` builds the checklist (``app.checklist``) for an asset and the wallets
chosen for its roles; ``obtain`` then gets every fact the checklist marks
automatic -- a session key from a session-key authority, a wallet key from a
wallet key authority, a fact a rule-based authority issues from what the wallet
holds -- and stores it in the wallet that needs it.
"""

import logging

from . import checklist, pdo_runner, registry_client, session_keys
from .credentials import PROJECT_OWNERSHIP, PUBLIC_KEY, WALLET_KEY, accepted, contract_id_of
from .did_utils import make_did

logger = logging.getLogger(__name__)


def _usable(user_name):
    """A session key is only worth presenting if its private half is here."""

    def usable(held):
        if held.type != PUBLIC_KEY:
            return True
        return session_keys.has_private_key(user_name, contract_id_of(held.subject), held.claims["key"])

    return usable


def _projects(wallets, trusted_issuers):
    """The projects the requester could declare: those their accepted facts are
    about, and those named by the project ownerships their wallets hold copies of
    (their PI's project, say, before any fact about it was issued to them)."""
    projects = set()
    for chosen in wallets.values():
        if chosen is None:
            continue
        holder, held = chosen
        for h in held:
            if h.type == PROJECT_OWNERSHIP:
                projects.add(h.claims["Owns"])
            elif h.is_about(holder) and "project" in h.claims and accepted(h, trusted_issuers):
                projects.add(h.claims["project"])
    return sorted(projects)


def assess(token_id, wallet_ids, user_name):
    """The checklist for using an asset with the wallets chosen so far.

    Returns ``{policy_id, requirements, trusted, rows, ready, needs_project,
    projects}``; each row also carries the fact's display name. ``needs_project``
    says a fact the asset needs is about a project, so the request must name the
    one this use is for.
    """
    policy_id = pdo_runner.resolve_policy_id(token_id, user_name)
    requirements = pdo_runner.get_policy_requirements(token_id, user_name)
    trusted = pdo_runner.list_trusted_issuers(policy_id, user_name)
    directory = registry_client.list_authorities()
    templates = registry_client.credential_templates_by_type()

    wallets = {
        role: (make_did(wallet_ids[role]), pdo_runner.wallet_credentials(wallet_ids[role], user_name))
        if role in wallet_ids else None
        for role in requirements
    }
    rows = checklist.checklist(
        requirements,
        trusted,
        wallets,
        directory,
        _usable(user_name),
        {t for t, v in templates.items() if v["self_asserted"]},
    )
    for row in rows:
        row["name"] = templates[row["type"]]["display_name"]

    needed = {t for types in requirements.values() for t in types}
    return {
        "policy_id": policy_id,
        "requirements": requirements,
        "trusted": trusted,
        "rows": rows,
        "ready": checklist.ready(rows),
        "needs_project": any("project" in templates[t]["json_schema"]["properties"] for t in needed),
        "projects": _projects(wallets, trusted),
    }


def _bind_session_key(authority_id, wallet_id, user_name):
    key_dir = session_keys.new_key_dir(user_name, wallet_id)
    try:
        pdo_runner.bind_session_key(authority_id, wallet_id, user_name, key_dir)
    except Exception:
        session_keys.discard(key_dir)
        raise
    return session_keys.keep(user_name, wallet_id, key_dir)


def obtain(rows, wallet_ids, user_name, request):
    """Get every fact the checklist marks automatic, asking rule-based authorities
    with ``request``. A rule-based authority reads its inputs from the wallet the
    fact is for. Returns what was obtained, as ``["<fact> from <authority>", ...]``."""
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
            inputs = {role: wallet_id for role in authority["inputs"]}
            vc = pdo_runner.issue_credential(authority_id, inputs, user_name, request)
            pdo_runner.wallet_add_vc(wallet_id, vc, user_name)
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
