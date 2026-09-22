"""Seed the template registry from files on disk.

Credential templates come from the ``credentials/`` folder (one JSON Schema per
credential) and policy templates come from the ``policy_cards/`` folder (one
subfolder per DUO). Their locations are taken from the ``CREDENTIALS_DIR`` and
``POLICY_CARDS_DIR`` environment variables, which are required -- the command
fails if either is unset (run.sh sets them from its path arguments).

The command reads everything it needs from those folders, so adding a credential
schema or a DUO -- or editing a rego module, its README, or its policy data
schema -- is picked up simply by re-running it. It is idempotent
(``update_or_create`` keyed on the natural unique field).

    python manage.py seed_templates
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from app.models import CredentialTemplate, PolicyTemplate

CREDENTIALS_DIR = Path(os.environ["CREDENTIALS_DIR"])
POLICY_CARDS_DIR = Path(os.environ["POLICY_CARDS_DIR"])

CREDENTIAL_SUFFIX = ".schema.json"


def _simplify(properties):
    """Project a JSON Schema ``properties`` object into a flat claims template
    (``{name: type-or-nested}``) usable as a fill-in hint when signing a VC."""
    out = {}
    for name, spec in (properties or {}).items():
        if not isinstance(spec, dict):
            out[name] = "string"
            continue
        kind = spec.get("type")
        if kind == "object" and "properties" in spec:
            out[name] = _simplify(spec["properties"])
        elif kind == "array":
            item_type = (spec.get("items") or {}).get("type", "string")
            out[name] = [item_type]
        else:
            out[name] = kind or "string"
    return out


def _template_name(duo_dir):
    """The registry name for a policy folder, from its path under POLICY_CARDS_DIR.

    Policies may be grouped in subfolders (``FL/inference-...``), so the name is the
    whole relative path rather than the leaf, joined with ``-`` to stay a flat
    identifier. A policy sitting directly under the root keeps exactly the name it
    had before grouping existed.
    """
    relative = duo_dir.relative_to(POLICY_CARDS_DIR)
    return "-".join(relative.parts).upper()


class Command(BaseCommand):
    help = (
        "Seed credential templates (from credentials/) and policy templates "
        "(from policy_cards/)."
    )

    def handle(self, *args, **options):
        self._seed_credentials()
        self._seed_policies()
        self.stdout.write(self.style.SUCCESS("Template registry seeded."))

    def _seed_credentials(self):
        count = 0
        for path in sorted(CREDENTIALS_DIR.glob(f"*{CREDENTIAL_SUFFIX}")):
            schema = json.loads(path.read_text())
            template_type = schema.get("$id") or path.name[: -len(CREDENTIAL_SUFFIX)]
            CredentialTemplate.objects.update_or_create(
                template_type=template_type,
                defaults={"claims_schema": _simplify(schema.get("properties", {}))},
            )
            self.stdout.write(f"  credential template: {template_type}")
            count += 1
        self.stdout.write(f"seeded {count} credential template(s)")

    def _seed_policies(self):
        count = 0
        for duo_dir in sorted(p.parent for p in POLICY_CARDS_DIR.rglob("policy.rego")):
            rego_path = duo_dir / "policy.rego"
            readme_path = duo_dir / "README.md"
            schema_path = duo_dir / "policy_data_schema.json"
            name = _template_name(duo_dir)
            PolicyTemplate.objects.update_or_create(
                name=name,
                defaults={
                    "rego_source": rego_path.read_text(),
                    "readme": readme_path.read_text() if readme_path.exists() else "",
                    "policy_data_schema": (
                        json.loads(schema_path.read_text())
                        if schema_path.exists()
                        else {}
                    ),
                },
            )
            self.stdout.write(f"  policy template: {name}")
            count += 1
        self.stdout.write(f"seeded {count} policy template(s)")
