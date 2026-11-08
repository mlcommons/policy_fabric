"""Credentials shaped the way the contracts store them."""

import base64
import json

from app.credentials import Held

REQUESTER = "did:pdo:requester"


def vc(type_, subject, claims=None, signer="registry", context_path=("poc",), issuer=None):
    credential = {
        "type": [type_],
        "issuer": {"id": issuer if issuer is not None else f"did:pdo:{signer}#{'/'.join(context_path)}"},
        "credentialSubject": {"subject": {"id": subject}, "claims": claims or {}},
    }
    return {
        "serializedCredential": base64.b64encode(json.dumps(credential).encode()).decode(),
        "proof": {
            "type": "ecdsa_secp384r1",
            "verificationMethod": {"id": signer, "context_path": list(context_path)},
            "proofValue": "c2ln",
        },
    }


def trusting(issuer_id, types, prefix_path=("poc",)):
    """A trusted-issuers map entry, as list_trusted_issuers returns it."""
    return {issuer_id: [{"verifying_context": {"prefix_path": list(prefix_path)}, "credential_types": list(types)}]}


def held(*vcs):
    """Credentials as a wallet's get_vc_list holds them, decoded."""
    return [Held(v, f"digest-{i}") for i, v in enumerate(vcs)]


def authority(did, name, kind, facts, **fields):
    """A directory entry, as the asset registry returns it."""
    return {
        "did": did,
        "name": name,
        "kind": kind,
        "facts": facts,
        "operator": "operator",
        "checks": "",
        "inputs": {},
        "sources": [],
        **fields,
    }
