"""Run a seed script before ``manage.py runserver``.

A seed is a plain Python file that drives some part of a PDO flow (much like
the rego-contract python tests) so the webapp comes up with contracts and
wallets already in place. It is run *after* ``bootstrap`` (which copies files
and populates the service registries) and *before* the dev server starts.

The seed file is executed with the webapp's own PDO state injected, so it can
call the decentralized helpers directly or go through the higher-level
``pdo_runner`` ops. These names are available as globals without importing:

    state      the shared PDO state (first arg to every decentralized helper)
    bindings   the shared PDO bindings
    runner     the app.pdo_runner module (create_wallet, create_asset_policy, ...)
    settings   the Django settings (SCRATCH_DIR, ASSET_REGISTRY_URL, ...)

Django is already set up when the seed runs, so it may also import and use the
app models (e.g. ``from app.models import AppConfig``) to persist UI state.

Anything else the seed needs (``pdo.identity...`` modules, json, etc.) it
imports itself, exactly like the test scripts do.
"""

import runpy
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ... import pdo_runner, pdo_state


class Command(BaseCommand):
    help = "Run a seed Python script (a PDO flow) before runserver."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the seed Python script.")
        parser.add_argument(
            "seed_args",
            nargs="*",
            help="Extra args forwarded to the seed script as sys.argv[1:].",
        )

    def handle(self, *args, **options):
        path = options["path"]
        seed_args = options["seed_args"]

        init_globals = {
            "state": pdo_state.get_state(),
            "bindings": pdo_state.get_bindings(),
            "runner": pdo_runner,
            "settings": settings,
        }

        self.stdout.write(f"Running seed: {path}")
        try:
            # run_name="__main__" so the seed's top-level code runs (and any
            # `if __name__ == "__main__"` block fires), matching the test scripts.
            saved_argv = sys.argv
            sys.argv = [path, *seed_args]
            try:
                runpy.run_path(path, init_globals=init_globals, run_name="__main__")
            finally:
                sys.argv = saved_argv
        except FileNotFoundError:
            raise CommandError(f"Seed script not found: {path}")
        except Exception as exc:
            raise CommandError(f"Seed failed: {exc}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
