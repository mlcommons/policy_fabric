"""URL-safe encoding of PDO contract ids.

PDO contract ids are standard-base64-encoded hashes, so they may contain
``+``, ``/``, and ``=``. None of those play well in URL path segments:
``/`` is the path delimiter, and ``+``/``=`` are reserved characters. We
remap the contract id with the URL-safe base64 alphabet (RFC 4648 §5):
``+`` → ``-`` and ``/`` → ``_``, then strip the ``=`` padding (the padding
length is recoverable from ``len(s) % 4``). The encoding is reversible.

This encoding is used *only* in URL paths the client_app builds for itself.
The raw contract id continues to be what we pass to PDO, the registry,
and what we embed in DIDs.
"""


def encode_cid(contract_id):
    """Map a base64 contract id to a URL-safe form."""
    return contract_id.replace("+", "-").replace("/", "_").rstrip("=")


def decode_cid(cid_url):
    """Invert :func:`encode_cid`. Re-pads ``=`` to a multiple of 4."""
    s = cid_url.replace("-", "+").replace("_", "/")
    pad = (-len(s)) % 4
    return s + ("=" * pad)
