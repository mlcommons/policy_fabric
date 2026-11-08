"""Accepted authorities, fact by fact.

A policy agent -- or a rule-based authority, which is configured exactly like
one -- trusts issuers per credential type. This module turns that map into what an
owner reads and edits: one row per fact, with the authorities accepted for it (by
name and kind, from the directory) and the ones the directory offers instead.
"""

from .credentials import contract_id_of, trusted_types
from .did_utils import parse_did

KIND_LABELS = {"hand-signing": "Hand-signing", "rule-based": "Rule-based", "system": "System"}


def describe(authority):
    return {
        "did": authority["did"],
        "contract_id": contract_id_of(authority["did"]),
        "name": authority["name"],
        "kind": authority["kind"],
        "kind_label": KIND_LABELS[authority["kind"]],
        "facts": authority["facts"],
        "operator": authority["operator"],
        "checks": authority["checks"],
        "inputs": authority["inputs"],
        "sources": authority["sources"],
    }


def options_for(fact, directory):
    """The directory's authorities for a fact, as panel options."""
    return [describe(a) for a in directory if fact in a["facts"]]


def panel(facts, trusted_issuers, directory, names):
    """One row per fact, with its display name from ``names``: who is accepted for
    it, and who else could be."""
    known = {contract_id_of(a["did"]): a for a in directory}
    rows = []
    for fact in facts:
        accepted = []
        for issuer_id in sorted(trusted_issuers):
            if fact not in trusted_types(trusted_issuers, issuer_id):
                continue
            if issuer_id in known:
                accepted.append(describe(known[issuer_id]))
            else:
                accepted.append({"did": f"did:pdo:{issuer_id}", "contract_id": issuer_id,
                                 "name": issuer_id, "kind": "unlisted", "kind_label": "unlisted"})
        accepted_ids = {a["contract_id"] for a in accepted}
        rows.append({
            "type": fact,
            "name": names[fact],
            "accepted": accepted,
            "options": [o for o in options_for(fact, directory) if o["contract_id"] not in accepted_ids],
        })
    return rows


def preselected(fact, directory):
    """A fact with a single system authority in the directory -- the session key,
    say -- is accepted by default."""
    options = options_for(fact, directory)
    return [o["did"] for o in options] if len(options) == 1 and options[0]["kind"] == "system" else []


def registrations(choices):
    """Group ``{fact: [authority DID, ...]}`` into one registration per authority
    and signing context: ``[(contract_id, path, [fact, ...])]``."""
    grouped = {}
    for fact, dids in choices.items():
        for did in dids:
            contract_id, path = parse_did(did)
            grouped.setdefault((contract_id, path or ""), []).append(fact)
    return [
        (contract_id, [path] if path else [], sorted(set(facts)))
        for (contract_id, path), facts in sorted(grouped.items())
    ]
