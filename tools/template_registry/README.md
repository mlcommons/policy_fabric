# template registry

A toy server simulating a registry of policy cards, policy components and
credential types. It is seeded at startup from the folders at the top of the
policy_fabric tree:

| Folder | Seeds | API |
|--------|-------|-----|
| `credentials/` | one `CredentialTemplate` per JSON Schema, with its display name, meaning, subject kinds and whether requesters assert it themselves | `/api/credentials/`, `/api/credentials/<id>/` |
| `policy_components/` | one `PolicyComponent` per component: its Rego, its `component.json` and the JSON Schema of its policy data | `/api/components/` |
| `policy_cards/` | one `PolicyTemplate` per card: its `graph.json`, the code, name and rule its `card.json` gives, its `policy_card.md`, and the guardian type its graph's grant fits | `/api/policies/?guardian_type=`, `/api/policies/<id>/` |

`/api/catalog/` is the policy catalog of the folders, built by
`tools/policy_catalog/build_catalog.py`, which the webapp draws policy graphs from.
Seeding checks the graphs, components and credential types against each other with
the same builder, and stops on any problem. `POST /api/policies/` checks the
template's `graph` the same way. A credential type is `presentable` (offered for signing) unless
a component produces it and its schema does not say `"x-presentable": true`.

```bash
./run.sh --interface 0.0.0.0 --port 8002 \
    --credentials-dir ../../credentials \
    --policy-cards-dir ../../policy_cards \
    --policy-components-dir ../../policy_components
```

Tests: `PYTHONPATH=../policy_catalog python manage.py test app` (they seed from the
repository's folders).
