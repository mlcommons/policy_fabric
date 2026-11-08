"""Verifiable credentials as the contracts store them, and whom a policy agent
accepts them from.

A stored credential is ``{serializedCredential, proof}``: the credential itself is
base64 JSON, and the proof names the signer (``verificationMethod.id``, a contract
id) and the signing context it signed from (``context_path``).
"""

import base64
import json

from .did_utils import DID_PREFIX, make_did

PUBLIC_KEY = "publicKeyCredential"
WALLET_KEY = "WalletVerifyingKeyCredential"
PROJECT_OWNERSHIP = "ProjectOwnershipCredential"


def contract_id_of(identifier):
    """The contract id an identifier names: a PDO DID without its prefix and
    fragment; anything else unchanged. Mirrors the contracts' ``contract_id_of``."""
    if not identifier.startswith(DID_PREFIX):
        return identifier
    return identifier[len(DID_PREFIX):].split("#", 1)[0]


class Held:
    """One credential in a wallet, decoded."""

    def __init__(self, vc, digest):
        self.vc = vc
        self.digest = digest
        credential = json.loads(base64.b64decode(vc["serializedCredential"]))
        method = vc["proof"]["verificationMethod"]
        self.type = credential["type"][0]
        self.issuer = credential["issuer"]["id"]
        self.subject = credential["credentialSubject"]["subject"]["id"]
        self.claims = credential["credentialSubject"]["claims"]
        self.signer = method["id"]
        self.context_path = method["context_path"]

    @property
    def signer_did(self):
        return make_did(self.signer)

    def is_about(self, did):
        return contract_id_of(self.subject) == contract_id_of(did)


def held_credentials(vc_map):
    """The credentials of a wallet's ``get_vc_list`` result, keyed by digest."""
    return [Held(vc, digest) for digest, vc in vc_map.items()]


def trusted_types(trusted_issuers, issuer_id):
    """The credential types a policy agent trusts ``issuer_id`` for, from any of
    its signing contexts."""
    if issuer_id not in trusted_issuers:
        return set()
    return {t for entry in trusted_issuers[issuer_id] for t in entry["credential_types"]}


def types_trusted_from(trusted_issuers, issuer_id, context_path):
    """The credential types a policy agent trusts ``issuer_id`` for when it signs
    from ``context_path``: those of the records whose prefix path it extends."""
    if issuer_id not in trusted_issuers:
        return set()
    types = set()
    for entry in trusted_issuers[issuer_id]:
        prefix = entry["verifying_context"]["prefix_path"]
        if context_path[: len(prefix)] == prefix:
            types.update(entry["credential_types"])
    return types


def accepted(held, trusted_issuers):
    """Whether a policy agent with these trusted issuers verifies this credential:
    its issuer is its signer, and the signer is trusted for its type from a
    context the proof's path extends."""
    if contract_id_of(held.issuer) != held.signer:
        return False
    return held.type in types_trusted_from(trusted_issuers, held.signer, held.context_path)


def accepted_issuers(trusted_issuers, credential_type):
    """The contract ids a policy agent trusts for a credential type."""
    return sorted(
        issuer_id
        for issuer_id in trusted_issuers
        if credential_type in trusted_types(trusted_issuers, issuer_id)
    )
