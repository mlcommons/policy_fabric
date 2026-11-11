"""Seed the template registry from files on disk.

Credential templates come from the ``credentials/`` folder (one JSON Schema per
credential type), policy components from ``policy_components/``, and policy
templates from ``policy_cards/``: every folder holding a ``graph.json`` is a card,
a graph of those components, named by its ``card.json``. The folders are taken
from the ``CREDENTIALS_DIR``, ``POLICY_CARDS_DIR`` and ``POLICY_COMPONENTS_DIR``
environment variables, which are required (run.sh sets them from its arguments).
The graphs, the components and the credential types are checked against each
other first, by the policy catalog builder; any problem stops the seeding.

Adding a card or a credential type, or editing one, is picked up by re-running
the command; it is idempotent (``update_or_create`` keyed on the name).

    python manage.py seed_templates
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from app.catalog import catalog
from app.models import CredentialTemplate, PolicyComponent, PolicyTemplate

CREDENTIALS_DIR = Path(os.environ["CREDENTIALS_DIR"])
POLICY_CARDS_DIR = Path(os.environ["POLICY_CARDS_DIR"])
# the guardian each grant a card's graph ends in fits
GUARDIAN_TYPES = {"grant_download": "download", "grant_inference": "inference"}

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


class Command(BaseCommand):
    help = (
        "Seed credential templates (from credentials/), policy components (from "
        "policy_components/) and policy templates (from policy_cards/)."
    )

    def handle(self, *args, **options):
        built = catalog()
        self._seed_credentials(built)
        self._seed_components(built)
        self._seed_policies(built)
        self.stdout.write(self.style.SUCCESS("Template registry seeded."))

    def _seed_credentials(self, built):
        count = 0
        for path in sorted(CREDENTIALS_DIR.glob(f"*{CREDENTIAL_SUFFIX}")):
            schema = json.loads(path.read_text())
            template_type = schema.get("$id") or path.name[: -len(CREDENTIAL_SUFFIX)]
            CredentialTemplate.objects.update_or_create(
                template_type=template_type,
                defaults={
                    "display_name": schema["displayName"],
                    "meaning": schema["meaning"],
                    "subject_kinds": schema["subjectKinds"],
                    "self_asserted": schema["selfAsserted"],
                    "json_schema": schema,
                    "claims_schema": _simplify(schema.get("properties", {})),
                    "presentable": built["credentials"][template_type]["presentable"],
                },
            )
            count += 1
        self.stdout.write(f"seeded {count} credential template(s)")

    def _seed_components(self, built):
        for component_id, component in built["components"].items():
            PolicyComponent.objects.update_or_create(
                component_id=component_id,
                defaults={
                    "package": component["package"],
                    "rego_source": component["rego"],
                    "metadata": {
                        k: v for k, v in component.items()
                        if k not in ("id", "rego", "package", "policy_data_schema")
                    },
                    "policy_data_schema": component["policy_data_schema"],
                },
            )
        self.stdout.write(f"seeded {len(built['components'])} policy component(s)")

    def _seed_policies(self, built):
        for folder, card in built["cards"].items():
            card_dir = POLICY_CARDS_DIR / folder
            manifest = json.loads((card_dir / "card.json").read_text())
            PolicyTemplate.objects.update_or_create(
                name=card["template"],
                defaults={
                    "code": manifest["code"],
                    "title": manifest["name"],
                    "rule": manifest["rule"],
                    "guardian_types": [GUARDIAN_TYPES[card["graph"]["root"]]],
                    "readme": (card_dir / "README.md").read_text(),
                    "graph": card["graph"],
                },
            )
            self.stdout.write(f"  policy template: {card['template']}")
        self.stdout.write(f"seeded {len(built['cards'])} policy template(s)")
