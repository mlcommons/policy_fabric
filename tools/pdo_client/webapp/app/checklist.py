"""The requester's readiness checklist: for every fact an asset needs, whether
the requester already has it, can get it on the way, or has someone to ask.

Built only from public data -- the asset's requirements and trusted issuers, the
directory of authorities, and the requester's own wallets -- so it can be shown
before anything is submitted.

| Status | Meaning |
|--------|---------|
| held | in the wallet, signed by an authority the asset trusts for that type |
| automatic | a trusted system or rule-based authority can issue it from what the wallet holds |
| ask | none can issue it on the way, but a hand-signing authority is accepted; the row names whom to ask |
| held_not_accepted | held, but signed by an authority the asset does not trust |
| unreachable | no accepted authority can issue it |

A self-asserted fact (a script's ownership, say) has no authority: one of the
requester's own identities signs it, and the policy checks the signature against
that identity's key. It is held once signed, and otherwise the requester is asked
to sign it.
"""

from .credentials import accepted, accepted_issuers, contract_id_of

HELD = "held"
AUTOMATIC = "automatic"
ASK = "ask"
HELD_NOT_ACCEPTED = "held_not_accepted"
UNREACHABLE = "unreachable"

READY = (HELD, AUTOMATIC)

HAND_SIGNING = "hand-signing"
RULE_BASED = "rule-based"
SYSTEM = "system"


def _by_contract(directory):
    return {contract_id_of(a["did"]): a for a in directory}


def can_issue_now(authority, wallet_types):
    """Whether an authority can issue from what the wallet holds: a system
    authority needs nothing the requester could lack; a rule-based one needs a
    credential of every input type it reads."""
    if authority["kind"] == SYSTEM:
        return True
    if authority["kind"] == RULE_BASED:
        needed = {t for types in authority["inputs"].values() for t in types}
        return needed <= wallet_types
    return False


def row(role, fact, trusted_issuers, about_holder, in_wallet, directory, usable):
    """One checklist row for one fact the asset needs under one role.

    ``about_holder`` are the role's credentials about its holder; ``in_wallet``
    everything the role's wallet holds, whoever it is about (an authority may
    read copies of credentials about others).
    """
    of_type = [h for h in about_holder if h.type == fact]
    held = [h for h in of_type if accepted(h, trusted_issuers) and usable(h)]

    known = _by_contract(directory)
    issuer_ids = accepted_issuers(trusted_issuers, fact)
    authorities = [known[i] for i in issuer_ids if i in known]
    unknown = [i for i in issuer_ids if i not in known]
    names = [a["name"] for a in authorities] + unknown

    out = {"role": role, "type": fact, "authorities": names, "via": None, "self_asserted": False}
    wallet_types = {h.type for h in in_wallet}
    automatic = [a for a in authorities if can_issue_now(a, wallet_types)]

    if held:
        out["status"] = HELD
    elif automatic:
        out["status"] = AUTOMATIC
        out["via"] = automatic[0]
    elif of_type:
        out["status"] = HELD_NOT_ACCEPTED
    elif any(a["kind"] == HAND_SIGNING for a in authorities) or unknown:
        out["status"] = ASK
        out["authorities"] = [a["name"] for a in authorities if a["kind"] == HAND_SIGNING] + unknown
    else:
        out["status"] = UNREACHABLE
    return out


def self_asserted_row(role, fact, about_holder, own):
    """A self-asserted fact is held when one of the requester's own identities
    (``own``, their contract ids) signed it in its own name."""
    signed = [
        h for h in about_holder
        if h.type == fact and h.signer in own and contract_id_of(h.issuer) == h.signer
    ]
    return {
        "role": role,
        "type": fact,
        "authorities": [],
        "via": None,
        "self_asserted": True,
        "status": HELD if signed else ASK,
    }


def checklist(requirements, trusted_issuers, wallets, directory, usable, self_asserted):
    """Rows for every fact an asset needs, in requirement order.

    ``wallets`` maps every role to ``(holder_did, held_credentials)`` for the
    identity chosen for it, or to ``None`` while none is chosen. ``usable`` says
    whether a held credential can be presented from here; ``self_asserted`` are
    the fact types the requester signs themselves.
    """
    own = {contract_id_of(chosen[0]) for chosen in wallets.values() if chosen is not None}
    rows = []
    for role, facts in requirements.items():
        chosen = wallets[role]
        holder, in_wallet = chosen if chosen is not None else (None, [])
        about_holder = [h for h in in_wallet if h.is_about(holder)]
        for fact in facts:
            if fact in self_asserted:
                rows.append(self_asserted_row(role, fact, about_holder, own))
            else:
                rows.append(row(role, fact, trusted_issuers, about_holder, in_wallet, directory, usable))
    return rows


def ready(rows):
    return all(r["status"] in READY for r in rows)
