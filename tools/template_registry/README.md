# template registry

A toy server simulating a registry of policy cards, authority cards and
credential types. It is seeded at startup from the folders at the top of the
policy_fabric tree:

| Folder | Seeds | API |
|--------|-------|-----|
| `credentials/` | one `CredentialTemplate` per JSON Schema, with its display name, meaning, subject kinds and whether requesters assert it themselves | `/api/credentials/` |
| `policy_cards/` | one `PolicyTemplate` per `card.json`: the policy cards and each guardian type's delivery module, with the facts they read and the JSON Schema of their parameters | `/api/policies/?guardian_type=&kind=` |
| `authority_cards/` | one `AuthorityTemplate` per `card.json`: a rule-based authority's rule, the fact it issues and the facts it reads | `/api/authorities/` |

A card on a rule template (`"template"` in its `card.json`) runs that template's
`policy.rego`.

```bash
./run.sh --interface 0.0.0.0 --port 8002 \
    --credentials-dir ../../credentials \
    --policy-cards-dir ../../policy_cards \
    --authority-cards-dir ../../authority_cards
```

Tests: `python manage.py test app` (they seed from the repository's folders).
