# Onboarding — for a Claude agent picking this up

You have been handed two checkouts that sit side by side:

```
<workspace>/
  policy_fabric/      this repo: policy cards, the toy registries, the guardians,
                     the FL server, and the webapp a person actually clicks
  pdo-contracts/     upstream Private Data Objects contract families, which
                     policy_fabric is a consumer of and never modifies
```

Read this file first, then read the two folders in the order it tells you to.
Everything below is written to be checked against the code rather than believed:
where it names a file, open it.

---

## 1. What this system is

A data holder wants to let someone else use their data without handing it over,
and wants a *rule* — not a person — to decide who may. The pieces that make that
work:

| Piece | Where | What it is |
| --- | --- | --- |
| **Asset** | `tools/asset_registry/` | a dataset or a script, named by a DID (`did:pdo:<contract_id>`), listed in a registry anyone can read |
| **Guardian** | `tools/guardians/` | the service standing in front of an asset. It holds the bytes and releases them only against a *capability* |
| **Policy** | `policy_cards/` | a Rego module, provisioned into a `rego_policy_agent` contract, that reads credentials and decides |
| **Credential** | `credentials/` | a signed statement about a subject — a person, a wallet, or a script |
| **Capability** | pdo-contracts | what a policy's approval turns into: a sealed instruction to one guardian to perform one operation |
| **Webapp** | `tools/pdo_client/webapp/` | a Django app driving a PDO client, and the only UI |
| **FL server** | `tools/fl_server/` | a job board several data holders connect to, so one script can run at all of them |

The load-bearing idea: **a policy never sees the data, a guardian never evaluates
a policy, and the requester never holds either.** A policy issues a
`policy_decision` credential; a token contract turns that into a capability bound
to one guardian; the guardian checks the capability and nothing else.

---

## 2. Read the two folders, in this order

### 2.1 `policy_fabric` — start here

Read these, in order. They are short and each one is the entry point to a layer.

1. `tools/README.md` — the component map, and how an inference asset is used.
2. `tools/guardians/README.md` — the contract between the webapp and a guardian:
   a folder with a `run.sh` and a `guardian.json`, and the vocabulary of launch
   values the manifest may draw on.
3. `tools/pdo_client/webapp/app/action_runners.py` — **the most important file in
   the repo.** One class per guardian type, each owning what the Use form
   collects, what the flow's steps are, and what comes back. Read the module
   docstring twice.
4. `tools/pdo_client/webapp/app/pdo_runner.py` — the contract operations, in one
   file, under one lock. Together with `ledger_client.py` (the user's contracts,
   read off CCF) and `pdo_state.py` (the client state they share), this is the
   whole seam between the two checkouts — those three files are the only ones
   that import `pdo.*`.
5. `tools/pdo_client/webapp/app/views/federated.py` — the federated round: how
   sites are discovered, how each one is asked separately, how the capabilities
   are handed over together.
6. `tools/fl_server/server.py` — no PDO in it at all. Read `ClientRegistry` and
   `RoundStore`.
7. `policy_cards/FL/README.md`, then one policy: `policy_cards/FL/
   inference-disease-specific-research/policy.rego`.
8. `docs/docs/tutorial_inference.md` — the whole thing as a story, and the
   document the browser test is an automation of.

### 2.2 `pdo-contracts` — read what the webapp actually calls

Do not try to read it all. The webapp touches four families; follow them from
`pdo_runner.py` outward:

| Family | Read | Why |
| --- | --- | --- |
| `rego-contract/` | `pdo/rego/decentralized/rego_token.py`, `pdo/rego/plugins/rego_token.py` | `create_capability` vs `do_operation` — the first mints a capability and hands it back, the second redeems it inline. The federated flow needs the first, because someone else contacts the guardian |
| `rego-contract/` | `pdo/rego/decentralized/rego_policy_agent.py` | `set_rego_policy`, `get_requirements`, `issue_policy_credential`, `register_trusted_issuer` |
| `identity-contract/` | `pdo/identity/decentralized/{identity,signature_authority}.py` | wallets are `identity.identity`; asset identities and manual issuers are `signature_authority`. `sign_with_contract_key` is what lets a wallet vouch for something in its own name |
| `authority-contract/` | `pdo/authority/decentralized/external_key_authority.py` | `bind_external_key`, and the wallet key authority created alongside it |
| `common-contract/` | `pdo/contracts/guardian/wsgi/{info,process_capability}.py` | the two endpoints every guardian serves. `process_capability` decrypts the operation out of the capability and dispatches to a handler |

The handler on the other side of that dispatch, for this repo, is
`tools/guardians/inference/guardian_core/inference.py` — 80 lines, and the place
where "the code that was approved" is compared against "the code that is running".

### 2.3 How the two relate

`pdo-contracts` is a **dependency**, consumed three ways:

- the `pdo.*` Python packages, imported by `pdo_runner.py` and `ledger_client.py`;
- the compiled contract `.wasm` binaries, installed under `$PDO_HOME/contracts`;
- the guardian service framework, which `tools/guardians/*/` extend by supplying
  a `capability_handler_map`.

Nothing in `policy_fabric` modifies `pdo-contracts`. The revision it is built from
is pinned at the top of `tools/docker_build_all.sh` — and the ledger, the enclave
services and the client must all come from that same revision, or every contract
creation fails.

---

## 3. The federated flow, which is the part most likely to confuse you

An asset behind an **inference** guardian is never used on its own. It is one
*site* of a *round*. The Assets page deliberately has no Use button for these;
the Federated page does the work.

```
registering an asset:  mint identity contract (asset gets a DID)
                            │
                            ▼
                       start the guardian, TOLD that DID
                            │
                            ▼
                       register in the asset registry
```

The DID must come first, because the inference guardian's bundled FL client
announces it:

```
FL client  ──POST /clients {client_id, asset_did}──►  FL server
                                                          │
Federated page ──GET /clients──────────────────────────────┘
   │ joins the answer against the asset registry, on the DID
   ▼
requester picks sites, one script, one role per policy (the union of them)
   │
   ▼
for each site: that site's own policy issues its own capability, or refuses
   │            (a refusal drops that site and nothing else)
   ▼
POST /rounds { script, participants: [{asset_did, capability}, ...] }
   │
   ▼
FL server hands each client the job addressed to the DID that client announced
   │
   ▼
each FL client re-hashes the script, redeems its capability at its own guardian,
runs, and reports metrics; the FL server aggregates them, weighted by samples
```

**The DID is the routing key.** That is the answer to "how does the FL server know
which capability is for whom": it does not infer it — each client says what it is
holding, and each capability is tagged with what it was minted for. A capability
is bound to one guardian and refused at every other, so any other scheme would be
guessing.

Things that follow from this, and that you should not "fix":

- A site refusing is **not** a failed round. `stream_events(..., fatal=...)` in
  `app/views/_streaming.py` is what makes per-site errors non-fatal, and the
  result panel lists them next to the sites that ran.
- Using an asset **never** starts an FL server. It is long-lived, containerized,
  and named by the requester on the Federated page; `tools/start_fl_server.sh`
  brings one up. The page does offer to start one — but only after a failed
  connection, as a separate explicit action (`app/fl_launcher.py`), because a
  federation normally has a server before it has members.
- When the webapp is containerized it has no Docker socket, so it writes a
  service's `run.sh` command into `GUARDIAN_DEPLOY_DIR` and a host-side watcher in
  `pdo_client/docker/run_webapp.sh` runs it. When the webapp runs on the host it
  runs the command itself. Guardians and the FL server both go through
  `app/service_launcher.py` for exactly this reason — it is the only part of
  launching a service that is not specific to the service.

---

## 4. A local PDO client

The webapp drives a real PDO client, which takes an hour-plus to build from
source. You do not need to: the client image already contains one, at the same
absolute paths a host install would use.

```bash
CID=$(docker create --entrypoint bash mlcommons/pdo_base_client:v2)
sudo rm -rf /pdo_install /pdo-contracts
sudo docker cp "$CID:/pdo_install"   /pdo_install
sudo docker cp "$CID:/pdo-contracts" /pdo-contracts
docker rm "$CID"
sudo chown -R "$(id -u):$(id -g)" /pdo_install /pdo-contracts
```

It works because the image is Ubuntu 22.04 and its virtualenv's base interpreter
is `/usr/bin/python3.10` — so on an Ubuntu 22.04 host the venv resolves exactly
as it did inside the container. **Check that first**; on any other host, build the
client properly (`tools/pdo_client/setup/setup.sh`) or run the webapp
containerized instead (`tools/docker_start_webapp.sh`).

Verify it:

```bash
export PDO_INSTALL_ROOT=/pdo_install PDO_CONTRACTS_ROOT=/pdo-contracts
source tools/pdo_client/setup/activate_env.sh
python -c "import pdo.common.crypto, pdo.rego.decentralized.rego_token; print('ok')"
```

Note that `/pdo-contracts` (the extracted copy, pinned to the image's revision) is
**not** the `pdo-contracts/` checkout beside this repo. Read the checkout; run
against the extracted copy.

---

## 5. Run the test, and record it

One command does the whole thing: brings up the ledger, the enclave services,
both registries, the FL server container and the webapp, then drives
`docs/docs/tutorial_inference.md` through a real browser and records it.

```bash
cd <workspace>/policy_fabric
PYTHON=<workspace>/venv/bin/python bash tools/tests/run_webui_inference_test.sh
```

About twenty minutes. `-k` leaves the stack up, `-p PORT` moves the webapp, `-n`
skips setup and drives whatever is already running (useful while iterating on the
test itself).

**Prerequisites**, all of which the run checks or fails loudly on:

| Thing | Check |
| --- | --- |
| Docker, ~20GB under `/var/lib/docker` | `df -h /var/lib/docker` |
| the images at `:v2` | `docker images \| grep mlcommons` — build with `tools/docker_build_all.sh` (comment out the `docker push` lines at the bottom first) |
| a bare-metal PDO client | section 4 |
| Google Chrome | `google-chrome --version`; selenium fetches its own driver |
| `Xvfb` | `which Xvfb` — **without it the run passes with no video**, which is not a pass for the purpose you were given |
| an ffmpeg | `which ffmpeg`, or `pip install imageio-ffmpeg` in the `$PYTHON` you point at |
| `selenium` in that same Python | `$PYTHON -c "import selenium"` |

`tools/tests/README.md` is the full recipe: what the run does step by step, what
each artifact is, and the failures that have actually happened here with their
causes. Read it before reporting a failure.

### What you should have at the end

```
/tmp/pdo_webui_artifacts/run.mp4     the browser, start to end, real time
/tmp/pdo_webui_artifacts/run_4x.mp4  the same thing, watchable
/tmp/pdo_fl_server.log               every client announcement and every round
/tmp/pdo_webapp.log                  the webapp
/tmp/pdo_scratch/guardian_run.log    what each guardian printed as it came up
```

Confirm the video before claiming one exists — a zero-length or undecodable file
is the normal failure mode here:

```bash
ffmpeg -hide_banner -i /tmp/pdo_webui_artifacts/run.mp4 2>&1 | grep -E 'Duration|Stream'
```

It should be roughly as long as the run took. Screenshots (`<step>.png`) in the
artifacts directory mean the run **failed**, whatever else it printed.

### Running it by hand instead

The pieces, in the order they have to start (this is what the runner does):

```bash
cd tools
bash docker_generate_user_keys.sh                     # /tmp/pdo_keys
bash docker_start_policy_engine.sh &                  # ledger, then services
#   wait for /tmp/pdo_ledger/ccf/keys/networkcert.pem
#   wait for /tmp/pdo_services/services/etc/site.toml
bash docker_start_registries.sh &                     # :8001 assets, :8002 templates
bash make_tutorial_files.sh                           # the cohorts and the script
bash start_fl_server.sh &                             # :7920 — BEFORE any guardian
PDO_INSTALL_ROOT=/pdo_install PDO_CONTRACTS_ROOT=/pdo-contracts \
    bash start_webapp.sh                              # :8000, on the host
```

Order matters in exactly one place: **the FL server must be up before any
inference guardian is registered**, because the guardian's FL client announces
itself once at startup. (It re-announces on every poll, so a late server recovers
within a few seconds — but the Federated page will show nothing until then.)

Tear down with `bash tools/stop_all.sh && bash tools/docker_stop_all.sh`.

---

## 6. Where things are, when you need to change one

| To change… | Edit |
| --- | --- |
| what a guardian type does when used | `webapp/app/action_runners.py` (a runner class) |
| how a guardian is launched | that guardian's `run.sh` + `guardian.json`, and `LAUNCH_VALUES` in `webapp/app/guardian_registry.py` if it needs a new value |
| where a service's launch command runs (here vs. handed to the host) | `webapp/app/service_launcher.py` — shared by guardians and the FL server |
| the federated page or the round | `webapp/app/views/federated.py`, `templates/federated/list.html`, `static/js/federated.js` |
| the FL server's API | `tools/fl_server/server.py` **and** `webapp/app/fl_client.py` **and** `guardians/inference/fl_framework/client.py` — three ends of one protocol |
| a policy | `policy_cards/<name>/policy.rego` + `policy_test.rego`; `opa test <dir> -v` |
| what the tutorial says | `docs/docs/tutorial_inference.md` **and** `tools/tests/webui_inference_test.py`, which is its automation. They drift apart silently; change both |

### Things that have bitten people here

- `__get_contract__` caches contract objects for 30 seconds, keyed on the save
  file. A read straight after a write through a fresh context can return the
  pre-write state for that long. Read the ledger's contract index instead.
- Docker silently creates a missing bind-mount source as a **root-owned
  directory**. `run_webapp.sh` checks its mounts are files for exactly this
  reason; a directory named `networkcert.pem` breaks every later run.
- A test killed by a signal leaves `ffmpeg` running and still writing `run.mp4`.
  The next run then has two writers and produces a video that will not decode.
  The runner kills strays first; if you start the test by hand, do too.
- The ledger, the enclave services and the client must be built from **one**
  pdo-contracts revision. Mixed revisions fail at contract registration with an
  error that does not mention versions.
