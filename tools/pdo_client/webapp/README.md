# client app

A local webapp for PDO interactions. It lives under `pdo_client/` and is built
into the same image as the PDO client (see `../Dockerfile`).

## Configuration

Configuration is passed to `run.sh` / `../docker/run_webapp.sh` as **args**, which export
the corresponding env vars (read by `config/settings.py`) before activating the
PDO env. There is no `.env` file — every value is required, supplied at launch.

`PDO_INSTALL_ROOT` and `PDO_CONTRACTS_ROOT` are *not* args; they must already be
set in the environment by the caller (set in the image; export them for a
bare-metal run). `run.sh` errors out if either is missing.

The only user-editable setting is the **public key / identity**, stored in the
database; everything else is deployment config supplied at launch.

Four values are read straight from the environment rather than taken as args,
because they are about a service this webapp *joins* rather than one it owns:

| Env var | What it is |
| --- | --- |
| `FL_SERVER_URL` | the FL server the Federated page offers first. A default, not a setting the flow reads — a round goes to whichever server the requester names |
| `FL_SERVER_URL_FROM_GUARDIAN` | how a guardian *container* names that same server. It cannot reach a host-published port as `localhost`, so this is the host-gateway alias the guardian's `run.sh` maps in |
| `FL_SERVER_DIR` | host path of `tools/fl_server`, for the one case where the Federated page offers to *start* a server because nothing is answering. Like `GUARDIANS_DIR` this names a path on the host, since that is where the command runs |
| `FL_SERVER_IMAGE` | the image that command runs |

## Build

The webapp is part of the merged PDO client image. Build it from the client
build script (one image for both the CLI and the webapp):

```
../build.sh --image <tag> \
    --repository <pdo-contracts-repo> --branch <branch> \
    --families "<contract families>"
```

## Docker run

`../docker/run_webapp.sh` runs that image and overrides its command with `run.sh` (which
sources `../setup/activate_env.sh` to activate the PDO env). Host files and the
scratch dir are bind-mounted onto fixed in-container paths, and all config is
forwarded to `run.sh` as args.

```
../docker/run_webapp.sh \
    --image <tag> \
    --interface 0.0.0.0 --port 8000 \
    --cert-path /path/to/networkcert.pem \
    --site-toml /path/to/site.toml \
    --keys-folder /path/to/user_keys \
    --scratch /path/to/host/scratch \
    --ledger-url http://ledger:6600 \
    --service-host myhost \
    --asset-registry-url http://assets:8001 \
    --template-registry-url http://templates:8002
```

## Local run

`run.sh` sources `../setup/activate_env.sh`, so export `PDO_INSTALL_ROOT` and
`PDO_CONTRACTS_ROOT` first (a bare-metal PDO install), then it takes the config
as args:

```
./run.sh \
    --interface 127.0.0.1 --port 8000 \
    --ledger-url http://localhost:6600 \
    --service-host localhost \
    --cert-path /path/to/networkcert.pem \
    --site-toml /path/to/site.toml \
    --keys-folder /path/to/user_keys \
    --scratch /path/to/scratch \
    --asset-registry-url http://localhost:8001 \
    --template-registry-url http://localhost:8002
```

## Seed (optional)

Pass `--seed PATH` to run a Python seed script after `bootstrap` and before the
dev server starts — a way to bring the webapp up with PDO state already in
place (run part of a flow, like the rego-contract python tests). It runs
via `manage.py seed`, which executes the file with these globals injected (no
imports needed): `state`, `bindings`, `runner` (`app.pdo_runner`), and
`settings`. Django is initialized, so the app models are importable too. See
`seeds/example_seed.py`.

For editor support (VS Code / Pylance) on the injected globals, import their
types under a `TYPE_CHECKING` guard — it's skipped at runtime but gives hover
and autocomplete on `runner.*`:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from seed_context import runner, state, bindings, settings
```

```
# bare metal
./run.sh ... --seed seeds/example_seed.py

# docker (the host script is bind-mounted into the container automatically)
../docker/run_webapp.sh ... --seed seeds/example_seed.py
```

## Policies

An asset's policy is a graph of policy components (see `policy_cards/README.md` and
`policy_components/README.md` at the top of the repository). The webapp reads every card, component
and credential type from the template registry's catalog (`/api/catalog/`, built by
`tools/policy_catalog/build_catalog.py`) and never runs Rego itself: the contract validates and runs
the graph.

| Where | What it does |
| --- | --- |
| `static/policy_ui/` | the graph renderer, shared with the docs site's Policy Composer: `PolicyGraph.layout` and `PolicyGraph.render` |
| `views/policies.py`, `templates/policies/list.html`, `static/js/policies.js` | the **Policies** page: every card drawn as its graph |
| `templates/_card_detail_modal.html`, `static/js/render.js` | a card's popup (`window.render.showCard`): its graph, its Policy Card, and its card component's Rego |
| `app/graphs.py`, `app/requirements.py` | composes the graphs of the cards an owner picks, and works out their requirement alternatives the way the contract's `set_rego_policy` expands them |
| `views/assets.py`, `static/js/asset_dashboard.js` | Expose (cards, each node's parameters, the authorities accepted per credential type) and an asset's dashboard |
| `app/trust.py` | the authorities offered and registered per credential type |
| `app/checklist.py`, `app/readiness.py` | the requester's checklist, and the credentials system authorities issue on the way |

**Composing cards.** The cards on one asset become one graph under one grant:

- node ids are component ids, so a component two cards share, such as ProjectMembership, is one node,
  with one set of parameters, and must be wired the same way in both cards ("The policies use
  `<node>` differently." otherwise);
- every card must end in the same grant ("The policies end in different grants" otherwise); its
  `grant` input takes every card's grant, and it issues the capability only when every card granted it;
- every type a card trusts is listed with no issuer; the owner's choice of authorities per type is
  registered with `register_trusted_issuer` after `set_rego_policy`.

Exposing is refused unless every type of at least one requirement alternative is accepted from some
authority, or signed by the requester's own wallet.

**Using an asset.** The checklist offers the alternative the requester is closest to, counting every
credential in the chosen wallets, whoever it is about, and the Use form presents that bundle.
Credentials a system authority issues, such as the session key, are obtained on the way.

## Cleanup

```
./cleanup.sh
```
