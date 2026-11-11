# asset registry

A toy server simulating an asset registry, and the directory of authorities.

| API | Holds |
|-----|-------|
| `/api/assets/`, `/api/assets/by_did/?did=` | assets, with the guardian and policy recorded in their metadata |
| `/api/authorities/`, `/api/authorities/by_did/?did=` | authorities: the DID they are trusted under, name, kind (`hand-signing` or `system`), operator, the credential types they issue and what they check |
| `/api/trust_lists/` | named lists of authorities, which an owner can accept in one click |

The webapp lists an authority here when it is created, so owners can find it
when they choose whom to accept. Creating an authority or a trust list requires
every one of its fields.

Tests: `python manage.py test app`.
