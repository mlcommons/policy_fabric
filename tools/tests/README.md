# Recipe — the federated inference tutorial, end to end, in a browser

Run [`docs/docs/tutorial_inference.md`](../../docs/docs/tutorial_inference.md)
from first click to last through the web UI, on a machine with no screen, and
come out with a video of it happening. Two hospitals, two inference guardians,
one federated round — and both of the FL policies, because Hospital B carries
FL-DS and FL-IS together.

**Done means:** the run prints `PASSED: 20 steps`, and there is one `run.mp4` of
the browser doing it.

## Parameters

`fix_problems` — given to you by whoever asked for the run.

- `False` — at the first thing that does not work, **stop**. Report the step, the
  command, the output, and which file and line you think is responsible. Change
  nothing.
- `True` — fix it, say plainly what you changed and why, then start the run again
  from the top. Never edit a test to make it pass, never delete a check to get
  past it, and never widen a timeout without saying you did.

Either way: report what actually happened. A step you skipped is a step you
report as skipped.

## What it needs

| Thing | Why |
| --- | --- |
| Docker | the policy engine, the registries, the guardians and the FL server |
| ~20GB free under `/var/lib/docker` | the PDO images |
| a bare-metal PDO client | the webapp runs on the host, not in a container — see `onboarding.md` |
| Google Chrome | selenium fetches its own driver |
| `Xvfb` | the display the browser draws on (`sudo apt-get install -y xvfb`) |
| `ffmpeg` | records that display (`pip install imageio-ffmpeg` also works) |
| `selenium` in the Python you point `$PYTHON` at | the clicking |

Without Xvfb or ffmpeg the run still passes, headless, with **no video at all**
— and says so on its first line. That is a failure of this recipe's goal; report
it rather than reporting a pass.

## 1. Check the codebase still matches this recipe

Do this first, every time. This recipe names files, form fields and policy names;
any of them can have moved.

```bash
cd <repo> && git log --oneline -5 && git status --short
```

These must exist:

| file | what this recipe uses it for |
| --- | --- |
| `tools/tests/run_webui_inference_test.sh` | brings the stack up and runs the test |
| `tools/tests/webui_inference_test.py` | the clicking |
| `tools/tests/recorder.py` | the display and the video |
| `tools/make_tutorial_files.sh` | writes the two cohorts and the script |
| `tools/start_fl_server.sh` | the job board every site connects to |
| `tools/start_webapp.sh` | the webapp, on this machine |
| `policy_cards/FL/inference-disease-specific-research/` | the first policy tested |
| `policy_cards/FL/inference-institution-specific-restriction/` | the second one |

And the images the stack runs must be present locally or pullable — the tags the
`tools/docker_*.sh` scripts name (`mlcommons/pdo_base_client`,
`mlcommons/toy_guardian`, `mlcommons/toy_inference_guardian`,
`mlcommons/pdo_fl_server`, plus the ledger, services and registry images). Build
them with `bash tools/docker_build_all.sh` if they are missing; that script also
pushes, so comment the pushes out if you only want them locally.

## 2. Run it

```bash
PYTHON=/path/to/venv/bin/python bash tools/tests/run_webui_inference_test.sh
```

Takes about fifteen minutes, most of it the ledger and enclave services coming
up. It tears the stack down afterwards; pass `-k` to leave it running.

| flag | effect |
| --- | --- |
| `-k` | keep the stack up after the test |
| `-n` | skip setup entirely and drive whatever is already running |
| `-H` | run headed on your own screen; records nothing |
| `-a DIR` | artifacts directory (default `/tmp/pdo_webui_artifacts`) |

It does all of this by itself: generates the user keys, starts the ledger and
enclave services, starts both registries, writes the tutorial files, starts the
FL server **container**, starts the webapp on the host, and then drives the
browser through the tutorial, once, in order:

1. the **script owner** publishes the script behind a public guardian, reads its
   DID, creates a wallet, and has that wallet sign a `ScriptOwnershipCredential`
   over the script with its own contract key;
2. the **trusted issuer** creates a manual issuer object and signs a
   `ScriptHashCredential` and an `IntendedDataUseCredential` about the script and
   an `AffiliationCredential` into the wallet, then creates a session-key issuer
   (which brings a wallet key authority with it);
3. **Hospital A** registers its cohort behind an inference guardian and attaches
   **FL-DS** alone;
4. **Hospital B** registers its own cohort behind its own guardian and attaches
   **FL-DS and FL-IS together** — two subpolicies of one policy agent, both of
   which must allow, with three trusted issuers between them;
5. the **script owner** opens **Federated**, sees both sites connected to the FL
   server, each by the FL client beside its guardian, selects both, and runs
   **one round** across them.

Three checks carry the weight, and all are about the thing being real rather
than the clicks working:

* the Use modal must ask for exactly `Script` **and** `User` — the union of what
  the two sites declared, not what either wants alone. Hospital A's FL-DS never
  asks about the requester; Hospital B's pair does;
* the round's aggregate `total_samples` must equal the two cohorts' real byte
  sizes added together (295 + 427 = 722). It only adds up if each guardian said
  yes and each FL client then ran over the file it actually holds;
* each hospital's job must have been run by the FL client beside **its own**
  guardian (`…:7900` for A, `…:7902` for B) — the client the FL server's
  DID -> client mapping names for that hospital's DID. The test reads that
  mapping off the Federated page, checks it against the FL server's own
  `GET /clients`, and then checks the round's result against it.

After the round the test also checks where the data is: each guardian core's
container must have **no** data mount, and each FL client's container must have
its hospital's cohort mounted. The guardian only answers yes or no; the dataset
belongs to the FL client.

A site whose policies refuse is reported in the result rather than failing the
flow, so the test also fails if any site comes back refused — otherwise a round
that quietly ran at one hospital would look like a pass.

## 3. What you should have at the end

```
/tmp/pdo_webui_artifacts/run.mp4     the browser, start to end, real time
/tmp/pdo_webui_artifacts/run_4x.mp4  the same thing, watchable
/tmp/pdo_webapp.log                  the webapp's own log
/tmp/pdo_fl_server.log               every client joining, and which client each round's jobs went to
/tmp/pdo_engine.log                  ledger + enclave services
/tmp/pdo_scratch/guardian_run.log    what each guardian printed as it came up
```

Check the video is real before reporting success — it should be about as long as
the run took:

```bash
ffmpeg -hide_banner -i /tmp/pdo_webui_artifacts/run.mp4 2>&1 | grep -E 'Duration|Stream'
```

The 4x copy is made for you by the same script; `run.mp4` is the authoritative
one.

Failure screenshots (`<step>.png`, `<step>.html`) only appear when a step fails.
If they are there, the run did not pass, whatever else it printed — the setup
clears the previous run's, so what you find is always this run's.

## 4. When something fails

The script prints the failing step, the browser's URL, a screenshot and the
page's HTML. Read those first. The video ends on the failure with the step name
in the caption bar, which is usually the quickest way to see what the browser was
looking at.

Things that have actually gone wrong here:

| symptom | cause |
| --- | --- |
| `No bare-metal PDO client at PDO_INSTALL_ROOT=...` | see `onboarding.md`; the webapp needs one on the host |
| `Timed out ... waiting for the enclave services` | a previous run's ledger container is still up on the old workspace; tear down and retry |
| every step fails at the identity dropdown | the webapp is up but its PDO client cannot reach the ledger — check `/tmp/pdo_webapp.log` |
| registering a cohort fails at "Waiting for the guardian to be healthy" | the inference guardian's core container did not come up; see `/tmp/pdo_scratch/guardian_run.log` |
| `sites [...] were not all ready within 120s` | a guardian is up but its FL client never announced — check that the FL server was running before the guardian started, and look for `client ... joined` in `/tmp/pdo_fl_server.log` |
| a site is listed with an FL client that is not `…:<its guardian's port>`, or `the FL server maps that DID to ...` | the FL server's DID -> client mapping disagrees with the site — look for `now holds` or `moves from client` in `/tmp/pdo_fl_server.log`, and for `the FL server refused this client` in `docker logs pdo-inference-guardian-<port>-fl-client` (a second client claiming a DID a connected one holds is refused with a `409`) |
| a site reports `no FL client holding this asset is connected to ...` | its FL client stopped polling between the page loading and the round being run; the flow drops that site before asking its policy |
| `step 'contract' failed: ... Replication task failed for request number N` | not this codebase. Look just above it in `/tmp/pdo_webapp.log` for `store_blocks ... Read timed out` — a PDO storage service (ports 72xx) did not answer within its 10s timeout while the new contract's state was being replicated, and the creation was abandoned. It happens under load; re-run on a quiet machine rather than retrying the step |
| a round hangs at "Waiting for ... to report" | that site's FL client crashed, or is polling a different FL server — `docker logs pdo-inference-guardian-<port>-fl-client` |
| a site reports `not allowed to run: the guardian said no (HTTP 422: operation failed)` | the digest the FL client computed does not match the one the capability authorizes — the script changed after its `ScriptHashCredential` was signed. The core logs both digests (`denied: ...`) in `/pdo_install/opt/pdo/logs/` inside `pdo-inference-guardian-<port>` |
| a site reports `not allowed to run: the guardian said no (HTTP 400: ...)` | the guardian refused the capability itself before comparing anything — typically one minted for a different guardian |
| `Not recording: Xvfb is not installed` | see the requirements table above |

## 5. Clean up

The script tears down after itself unless you passed `-k`. To do it by hand:

```bash
bash tools/stop_all.sh
bash tools/docker_stop_all.sh
```
