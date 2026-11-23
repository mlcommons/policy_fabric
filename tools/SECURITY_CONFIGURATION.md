# Registry and web client deployment

All three Django services require `DJANGO_SECRET_KEY` in the environment. Generate
an independent persistent key for each service, for example with
`python -c 'import secrets; print(secrets.token_urlsafe(64))'`. Keep it outside source
control. `DJANGO_DEBUG` defaults to false. Set `DJANGO_ALLOWED_HOSTS` to the
comma-separated hostnames clients actually use; the default permits loopback only.
These environment variables are forwarded by the Docker launchers.

Registry GET requests remain public. Every registry API write requires
`Authorization: Bearer <token>`. Set `REGISTRY_WRITE_TOKEN` independently for each
registry using a random secret (for example `secrets.token_urlsafe(32)`). An unset
token disables writes. Send tokens over HTTPS, and never place them in URLs,
browser JavaScript, or committed files. Cookie sessions do not authorize API writes,
so these bearer-only endpoints do not depend on browser CSRF cookies.

Set the web client's `ASSET_REGISTRY_WRITE_TOKEN` to the asset registry's token.
The server-side registry client supplies the header for asset creation and metadata
updates. Keep the web client behind trusted access controls: it is a reference
application that performs privileged operations for its users, not a public
multi-tenant authorization boundary. Do not expose it directly to untrusted users.

The registry launchers no longer create an `admin/admin` account. If the Django
admin is needed, create an account explicitly using `manage.py createsuperuser`.
Seeding templates from local files remains available through `seed_templates`.
For local development, explicitly export a random key and token, then launch the
services as before. To use another development hostname, add it to allowed hosts;
enable debug explicitly only on a trusted local development machine.

Run regression tests separately for the two Django projects:

```sh
DJANGO_SECRET_KEY=test-only-key python tools/asset_registry/manage.py test app
DJANGO_SECRET_KEY=test-only-key python tools/template_registry/manage.py test app
```
