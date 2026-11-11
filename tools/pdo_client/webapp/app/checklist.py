"""The requester's readiness checklist: for every credential an asset's policy
takes presented, whether the requester already has it, can get it on the way, or
has someone to ask.

Built only from public data -- the asset's requirements and trusted issuers, the
directory of authorities, and the requester's own wallets -- so it can be shown
before anything is submitted. A wallet holds credentials about its holder and
copies of credentials about others (the PI's project ownership, say), and the
policy's components read both, so any credential of the type counts.

| Status | Meaning |
|--------|---------|
| held | in the wallet, signed by an authority the asset trusts for that type |
| automatic | a trusted system authority issues it on the way |
| ask | none can issue it on the way, but a hand-signing authority is accepted; the row names whom to ask |
| held_not_accepted | held, but signed by an authority the asset does not trust |
| unreachable | no accepted authority can issue it |

A self-asserted credential (a script's ownership, say) has no authority: one of
the requester's own identities signs it, and the policy checks the signature
against that identity's key. It is held once signed, and otherwise the requester
is asked to sign it.
"""

from .credentials import accepted, accepted_issuers, contract_id_of

HELD = "held"
AUTOMATIC = "automatic"
ASK = "ask"
HELD_NOT_ACCEPTED = "held_not_accepted"
UNREACHABLE = "unreachable"

READY = (HELD, AUTOMATIC)

HAND_SIGNING = "hand-signing"
SYSTEM = "system"


def _by_contract(directory):
    return {contract_id_of(a["did"]): a for a in directory}


def row(role, fact, trusted_issuers, in_wallet, directory, usable):
    """One checklist row for one credential type the asset needs under one role,
    from everything the role's wallet holds."""
    of_type = [h for h in in_wallet if h.type == fact]
    held = [h for h in of_type if accepted(h, trusted_issuers) and usable(h)]

    known = _by_contract(directory)
    issuer_ids = accepted_issuers(trusted_issuers, fact)
    authorities = [known[i] for i in issuer_ids if i in known]
    unknown = [i for i in issuer_ids if i not in known]
    names = [a["name"] for a in authorities] + unknown

    out = {"role": role, "type": fact, "authorities": names, "via": None, "self_asserted": False}
    # a system authority needs nothing the requester could lack
    automatic = [a for a in authorities if a["kind"] == SYSTEM]

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


def self_asserted_row(role, fact, in_wallet, own):
    """A self-asserted credential is held when one of the requester's own
    identities (``own``, their contract ids) signed it in its own name."""
    signed = [
        h for h in in_wallet
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
    """Rows for every credential type an alternative of the asset's requirements
    names, in requirement order.

    ``wallets`` maps every role to ``(holder_did, held_credentials)`` for the
    identity chosen for it, or to ``None`` while none is chosen. ``usable`` says
    whether a held credential can be presented from here; ``self_asserted`` are
    the types the requester signs themselves.
    """
    own = {contract_id_of(chosen[0]) for chosen in wallets.values() if chosen is not None}
    rows = []
    for role, facts in requirements.items():
        chosen = wallets[role]
        in_wallet = chosen[1] if chosen is not None else []
        for fact in facts:
            if fact in self_asserted:
                rows.append(self_asserted_row(role, fact, in_wallet, own))
            else:
                rows.append(row(role, fact, trusted_issuers, in_wallet, directory, usable))
    return rows


def ready(rows):
    return all(r["status"] in READY for r in rows)
