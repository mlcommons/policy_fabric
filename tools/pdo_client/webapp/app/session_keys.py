"""Per-(user, wallet) session keys.

A session key is the RSA key pair a session-key authority binds to a wallet (see
``pdo.authority.session_key`` / ``cmd_bind_external_key``) when it issues the
wallet a ``publicKeyCredential``. The guardian encrypts downloaded data to the
credential's public key, and the user decrypts the result with the matching
private key kept here.

A wallet can hold several -- one per authority that bound one -- so each key pair
lives in its own folder, named by a fingerprint of its public key:
``settings.SESSION_KEYS_DIR/<user_name>/<wallet_id>/<fingerprint>/``, holding
``session_rsa_private.pem`` / ``session_rsa_public.pem`` as
``pdo.authority.session_key.generate_rsa_keypair`` writes them.
"""

import hashlib
import os
import re
import shutil
import tempfile

from django.conf import settings

from .url_safe_id import encode_cid

_PRIVATE_KEY_FILENAME = "session_rsa_private.pem"
_PUBLIC_KEY_FILENAME = "session_rsa_public.pem"


def _safe_user(user_name):
    """Filesystem-safe folder name for a user identity."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", user_name or "") or "unknown"


def fingerprint(public_pem):
    return hashlib.sha256(public_pem.strip().encode()).hexdigest()[:16]


def wallet_dir(user_name, wallet_id):
    return os.path.join(settings.SESSION_KEYS_DIR, _safe_user(user_name), encode_cid(wallet_id))


def _private_key_path(user_name, wallet_id, public_pem):
    return os.path.join(wallet_dir(user_name, wallet_id), fingerprint(public_pem), _PRIVATE_KEY_FILENAME)


def has_private_key(user_name, wallet_id, public_pem):
    """True when this machine holds the private half of a bound key."""
    return os.path.isfile(_private_key_path(user_name, wallet_id, public_pem))


def new_key_dir(user_name, wallet_id):
    """A fresh folder for a key about to be generated and bound."""
    parent = wallet_dir(user_name, wallet_id)
    os.makedirs(parent, exist_ok=True)
    return tempfile.mkdtemp(prefix="binding_", dir=parent)


def keep(user_name, wallet_id, key_dir):
    """File a freshly bound key pair under its fingerprint; returns its public key."""
    with open(os.path.join(key_dir, _PUBLIC_KEY_FILENAME)) as f:
        public_pem = f.read()
    target = os.path.join(wallet_dir(user_name, wallet_id), fingerprint(public_pem))
    if os.path.isdir(target):
        shutil.rmtree(key_dir)
    else:
        os.rename(key_dir, target)
    return public_pem


def discard(key_dir):
    shutil.rmtree(key_dir, ignore_errors=True)


def decrypt_download(user_name, wallet_id, encrypted_path, channel_key):
    """Decrypt a downloaded file with the private half of ``channel_key`` and
    return the plaintext as text."""
    from session_keys_utils.read_data import read_data

    fd, decrypted_path = tempfile.mkstemp(
        prefix="session_dec_", suffix=".bin", dir=settings.SCRATCH_DIR
    )
    os.close(fd)
    try:
        read_data(
            encrypted_path, _private_key_path(user_name, wallet_id, channel_key), decrypted_path
        )
        with open(decrypted_path, "rb") as f:
            return f.read().decode(errors="replace")
    finally:
        try:
            os.unlink(decrypted_path)
        except OSError:
            pass
