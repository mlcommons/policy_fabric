"""DID parsing and construction utilities.

DID format follows the W3C DID syntax with ``#`` as the fragment separator:

    did:pdo:<contract_id>                — the contract as a whole (a wallet)
    did:pdo:<contract_id>#<context_path> — a specific signing context inside it

``contract_id`` is treated as opaque and may itself contain ``/`` characters,
which is why we use ``#`` (not ``/``) to delimit the signing-context path.
Multi-segment context paths are still joined with ``/`` *inside* the fragment
(e.g. ``did:pdo:<id>#foo/bar``).
"""

DID_PREFIX = "did:pdo:"
PATH_SEP = "#"


def parse_did(did):
    """Parse a PDO DID string.

    Returns ``(contract_id, context_path)`` where ``context_path`` is ``None``
    when no fragment is present.

    Examples:
        parse_did("did:pdo:abc/123")          -> ("abc/123", None)
        parse_did("did:pdo:abc/123#mypath")   -> ("abc/123", "mypath")
        parse_did("did:pdo:abc#a/b")          -> ("abc", "a/b")
    """
    if not did.startswith(DID_PREFIX):
        raise ValueError(f"Invalid PDO DID: {did!r}")

    rest = did[len(DID_PREFIX) :]
    if PATH_SEP in rest:
        # rsplit so that any stray '#' inside the contract_id (shouldn't happen,
        # but defensively) stays on the contract_id side.
        contract_id, context_path = rest.rsplit(PATH_SEP, 1)
        return contract_id, context_path
    return rest, None


def make_did(contract_id, path=None):
    """Construct a PDO DID string.

    ``path`` may be a string (``"foo"`` or ``"foo/bar"``) or a list of
    segments (``["foo", "bar"]``); both produce ``did:pdo:<id>#foo/bar``.

    Examples:
        make_did("abc/123")                  -> "did:pdo:abc/123"
        make_did("abc/123", "mypath")        -> "did:pdo:abc/123#mypath"
        make_did("abc", ["foo", "bar"])      -> "did:pdo:abc#foo/bar"
    """
    if not path:
        return f"{DID_PREFIX}{contract_id}"
    if isinstance(path, (list, tuple)):
        path = "/".join(path)
    return f"{DID_PREFIX}{contract_id}{PATH_SEP}{path}"
