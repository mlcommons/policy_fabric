# The documentation site

The MkDocs site published at <https://docs.mlcommons.org/policy_fabric/>: the overview, the
three tutorials and the Policy Composer.

| Path | Holds |
| --- | --- |
| `docs/` | the pages, in the order `mkdocs.yml`'s `nav` gives |
| `composer/` | the Policy Composer app: plain HTML, CSS and JavaScript, no build step |
| `hooks/policy_catalog.py` | adds the composer, its renderer and the policy catalog to the site at build time |
| `mkdocs.yml`, `requirements.txt` | the site's configuration and what building it needs |

The composer draws graphs with the PDO client's renderer,
`tools/pdo_client/webapp/static/policy_ui/`, and reads `catalog.json`, which the hook builds
with `tools/policy_catalog/build_catalog.py` from `credentials/`, `policy_components/` and
`policy_cards/`. Neither is committed under `docs/`, and any catalog problem fails the build.

## Building it

```bash
pip install -r docs/requirements.txt
mkdocs serve -f docs/mkdocs.yml            # http://127.0.0.1:8000/, the composer at /composer/
mkdocs build --strict -f docs/mkdocs.yml   # writes docs/site/, as CI does
```

`mkdocs serve` rebuilds when the composer, the renderer, the catalog builder, or a credential,
component or card changes. Opening `composer/index.html` straight from disk does not work: the
page fetches `catalog.json`, which only a build produces.

## Testing the composer

```bash
pip install playwright && playwright install chromium
mkdocs build --strict -f docs/mkdocs.yml
python3 tools/tests/policy_ui/e2e_composer.py docs/site /tmp/composer-shots
```

It serves the built site and drives the composer in Chromium: the library, loading and
downloading every card, building the IRB card from the library, wiring, accept presented,
Simulate, Arrange, the draft kept on reload, the framing docs page, both themes and phone
width. It prints a PASS or FAIL line per check, saves screenshots, and exits 1 on any failure.
CI does not run it; CI builds the site strictly (`.github/workflows/policy-checks.yml`) and
deploys it on pushes to `main` (`.github/workflows/docs.yml`).
