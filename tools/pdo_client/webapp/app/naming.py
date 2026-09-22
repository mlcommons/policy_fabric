"""Local (DID -> name) mapping for wallets and issuers.

The ledger's contract list (``ledger_client``) has no notion of a display
name — contracts are addressed by DID everywhere else. This is a purely
local UI layer on top of it: a display name a user chose, remembered by DID.
"""

from .models import ContractName

UNKNOWN = "UNKNOWN"


def set_name(did, name):
    """Create or update the local display name for ``did``."""
    ContractName.objects.update_or_create(did=did, defaults={"name": name})


def get_name(did):
    """Return the local display name for ``did``, or ``UNKNOWN`` if unset."""
    entry = ContractName.objects.filter(did=did).first()
    return entry.name if entry else UNKNOWN


def get_names(dids):
    """Bulk lookup: ``{did: name}`` for every did in ``dids``.

    DIDs with no local entry map to ``UNKNOWN``.
    """
    found = dict(ContractName.objects.filter(did__in=dids).values_list("did", "name"))
    return {did: found.get(did, UNKNOWN) for did in dids}
