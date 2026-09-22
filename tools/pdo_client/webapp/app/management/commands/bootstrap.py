"""One-shot bootstrap to be run before ``manage.py runserver``.

Copies the network cert, ``site.toml``, and user keys into ``PDO_HOME``,
then populates the local service registries (eservice / pservice /
sservice / service_db). Idempotent — safe to re-run on every start.

The dev server itself does not run any of this; it picks up the
on-disk state lazily via ``pdo_state.get_state()`` on first use.
"""

import logging
import os
import shutil

from django.conf import settings as cfg
from django.core.management.base import BaseCommand

from ... import pdo_state

logger = logging.getLogger(__name__)


def _copy_files():
    os.makedirs(cfg.SCRATCH_DIR, exist_ok=True)
    os.makedirs(cfg.DOWNLOAD_OUTPUT_DIR, exist_ok=True)

    os.makedirs(cfg.PDO_LEDGER_KEY_ROOT, exist_ok=True)
    src_cert = cfg.LEDGER_CERT_PATH
    if os.path.exists(src_cert):
        shutil.copy(src_cert, cfg.PDO_LEDGER_KEY_ROOT)
    else:
        logger.warning("network cert not found at %s — skipping copy", src_cert)

    os.makedirs(os.path.dirname(cfg.F_SERVICE_SITE_FILE), exist_ok=True)
    src_cert = cfg.SITE_TOML_SOURCE
    if os.path.exists(src_cert):
        shutil.copy(src_cert, cfg.F_SERVICE_SITE_FILE)
    else:
        logger.warning("site.toml not found at %s — skipping copy", src_cert)

    keys_dir = os.path.join(cfg.PDO_HOME, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    if os.path.isdir(cfg.USER_KEYS_FOLDER):
        for fname in os.listdir(cfg.USER_KEYS_FOLDER):
            src = os.path.join(cfg.USER_KEYS_FOLDER, fname)
            if os.path.isfile(src):
                shutil.copy(src, keys_dir)
    else:
        logger.warning("user keys folder %s missing", cfg.USER_KEYS_FOLDER)


def _populate_service_registries(state, bindings):
    from pdo.client.commands.eservice import do_eservice
    from pdo.client.commands.pservice import do_pservice
    from pdo.client.commands.service_db import do_service_db
    from pdo.client.commands.sservice import do_sservice

    do_service_db(state, bindings, ["import", "--file", cfg.F_SERVICE_SITE_FILE])
    do_eservice(
        state,
        bindings,
        [
            "create_from_site",
            "--file",
            cfg.F_SERVICE_SITE_FILE,
            "--group",
            "default",
            "--preferred",
            cfg.PREFERRED_ESERVICE_URL,
        ],
    )
    do_pservice(
        state,
        bindings,
        [
            "create_from_site",
            "--file",
            cfg.F_SERVICE_SITE_FILE,
            "--group",
            "default",
        ],
    )
    do_sservice(
        state,
        bindings,
        [
            "create_from_site",
            "--file",
            cfg.F_SERVICE_SITE_FILE,
            "--group",
            "default",
            "--replicas",
            "5",
            "--duration",
            "999999999",
        ],
    )


class Command(BaseCommand):
    help = "Copy PDO files and populate local service registries. Run before runserver."

    def handle(self, *args, **options):
        _copy_files()
        state, bindings = pdo_state.get_state(), pdo_state.get_bindings()
        _populate_service_registries(state, bindings)
        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))
