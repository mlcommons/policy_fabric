"""Seed the template registry from files on disk.

Credential templates come from the ``credentials/`` folder (one JSON Schema per
credential type). Policy and delivery templates come from the ``policy_cards/``
folder and authority templates from ``authority_cards/``: every folder holding a
``card.json`` is a card, whose rule is its own ``policy.rego`` or the one of the
rule template it names. The folders are taken from the ``CREDENTIALS_DIR``,
``POLICY_CARDS_DIR`` and ``AUTHORITY_CARDS_DIR`` environment variables, which
are required (run.sh sets them from its arguments).

Adding a card or a credential type, or editing one, is picked up by re-running
the command; it is idempotent (``update_or_create`` keyed on the name).

    python manage.py seed_templates
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from app.models import AuthorityTemplate, CredentialTemplate, PolicyTemplate

CREDENTIALS_DIR = Path(os.environ["CREDENTIALS_DIR"])
POLICY_CARDS_DIR = Path(os.environ["POLICY_CARDS_DIR"])
AUTHORITY_CARDS_DIR = Path(os.environ["AUTHORITY_CARDS_DIR"])

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


def _template_name(card_dir, root):
    """The registry name for a card folder: its path under the root, joined with
    ``-`` and upper-cased, so ``FL/inference-...`` stays one flat identifier. It is
    also the module id the policy agent keys the card's policy data by."""
    return "-".join(card_dir.relative_to(root).parts).upper()


def _card(card_dir):
    """A card's manifest, the rule it runs -- its template's, when it names one --
    and its README."""
    manifest = json.loads((card_dir / "card.json").read_text())
    if "template" in manifest:
        rule = POLICY_CARDS_DIR / "templates" / manifest["template"] / "policy.rego"
    else:
        rule = card_dir / "policy.rego"
    return manifest, rule.read_text(), (card_dir / "README.md").read_text()


class Command(BaseCommand):
    help = (
        "Seed credential templates (from credentials/), policy and delivery "
        "templates (from policy_cards/) and authority templates (from "
        "authority_cards/)."
    )

    def handle(self, *args, **options):
        self._seed_credentials()
        self._seed_policies()
        self._seed_authorities()
        self.stdout.write(self.style.SUCCESS("Template registry seeded."))

    def _seed_credentials(self):
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
                },
            )
            count += 1
        self.stdout.write(f"seeded {count} credential template(s)")

    def _seed_policies(self):
        count = 0
        for card_dir in sorted(p.parent for p in POLICY_CARDS_DIR.rglob("card.json")):
            manifest, source, readme = _card(card_dir)
            name = _template_name(card_dir, POLICY_CARDS_DIR)
            policy = manifest["kind"] == PolicyTemplate.POLICY
            PolicyTemplate.objects.update_or_create(
                name=name,
                defaults={
                    "kind": manifest["kind"],
                    # a policy has a code; a delivery module names an operation
                    "code": manifest["code"] if policy else "",
                    "title": manifest["name"],
                    "rule": manifest["rule"],
                    "guardian_types": manifest["guardianTypes"],
                    "requirements": manifest["facts"],
                    "parameters_schema": manifest["parameters"],
                    # a preset, for the cards that ship one
                    "defaults": manifest["defaults"] if "defaults" in manifest else {},
                    "operation": "" if policy else manifest["operation"],
                    "rego_source": source,
                    "readme": readme,
                },
            )
            self.stdout.write(f"  {manifest['kind']} template: {name}")
            count += 1
        self.stdout.write(f"seeded {count} policy template(s)")

    def _seed_authorities(self):
        count = 0
        for card_dir in sorted(p.parent for p in AUTHORITY_CARDS_DIR.rglob("card.json")):
            manifest, source, readme = _card(card_dir)
            name = _template_name(card_dir, AUTHORITY_CARDS_DIR)
            AuthorityTemplate.objects.update_or_create(
                name=name,
                defaults={
                    "title": manifest["name"],
                    "rule": manifest["rule"],
                    "issues": manifest["issues"],
                    "presenters": manifest["presenters"],
                    "requirements": manifest["facts"],
                    "parameters_schema": manifest["parameters"],
                    "rego_source": source,
                    "readme": readme,
                },
            )
            self.stdout.write(f"  authority template: {name}")
            count += 1
        self.stdout.write(f"seeded {count} authority template(s)")
