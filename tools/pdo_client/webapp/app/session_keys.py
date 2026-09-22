"""Per-(user, wallet) session keys.

A session key is the RSA key pair an external_key_authority generates and
binds to a specific wallet (see ``pdo.authority.session_key`` /
``cmd_bind_external_key``) when it issues that wallet a ``publicKeyCredential``.
The guardian encrypts downloaded data to the credential's public key, and the
user decrypts the result with the matching private key kept here.

Keys live under ``settings.SESSION_KEYS_DIR/<user_name>/<wallet_id>/`` as
``session_rsa_private.pem`` / ``session_rsa_public.pem`` — the exact
filenames ``pdo.authority.session_key.generate_rsa_keypair`` writes, since
that module (not this one) is what actually generates them.
"""

import os
import re
import tempfile

from django.conf import settings

from .url_safe_id import encode_cid

_PRIVATE_KEY_FILENAME = "session_rsa_private.pem"


def _safe_user(user_name):
    """Filesystem-safe folder name for a user identity."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", user_name or "") or "unknown"


def keys_dir(user_name, wallet_id):
    return os.path.join(
        settings.SESSION_KEYS_DIR, _safe_user(user_name), encode_cid(wallet_id)
    )


def _private_key_path(user_name, wallet_id):
    return os.path.join(keys_dir(user_name, wallet_id), _PRIVATE_KEY_FILENAME)


def has_session_key(user_name, wallet_id):
    """True once a session key has been bound to this wallet."""
    return os.path.isfile(_private_key_path(user_name, wallet_id))


def decrypt_download(user_name, wallet_id, encrypted_path):
    """Decrypt a downloaded (encrypted) file with the wallet's session
    private key and return the plaintext as text.
    """
    from session_keys_utils.read_data import read_data

    fd, decrypted_path = tempfile.mkstemp(
        prefix="session_dec_", suffix=".bin", dir=settings.SCRATCH_DIR
    )
    os.close(fd)
    try:
        read_data(
            encrypted_path, _private_key_path(user_name, wallet_id), decrypted_path
        )
        with open(decrypted_path, "rb") as f:
            return f.read().decode(errors="replace")
    finally:
        try:
            os.unlink(decrypted_path)
        except OSError:
            pass
