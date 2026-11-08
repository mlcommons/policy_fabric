"""The federated inference tutorial, driven through the web UI.

Every click `docs/docs/tutorial_inference.md` asks a reader to make, made by a
browser instead, in the same order and with nothing added:

* the script owner publishes their code behind a public guardian, gets a wallet,
  and has that wallet claim the script;
* the trusted issuer creates a hand-signing authority that vouches for the code
  (digest, declared diseases) and for the requester (institution), and a system
  authority that attests wallet keys;
* **Hospital A** puts its cohort behind an inference guardian under **FL-DS**;
* **Hospital B** puts its own cohort behind its own guardian under **FL-DS and
  FL-IS together** -- modules of one policy agent, all of which must allow;
* the script owner checks each site's readiness checklist and runs **one round**
  across both, filling the union of the roles the two sites ask for, and gets
  per-site metrics and one aggregate back.

What the run proves, beyond "it works": the aggregate's ``total_samples`` is the
sum of the two cohorts' real sizes, so it only adds up if each guardian said yes
and each FL client then ran over the file it actually holds; the data is mounted
into the FL clients' containers and into neither guardian core's; the Use form
asks for exactly ``Script`` and ``User``, which is the union of what A and B
declared and not what either asked for alone; each site's checklist says what the
requester holds and what is obtained on the way; and each hospital's job was run
by the FL client beside its own guardian -- the client the FL server's DID ->
client mapping names for that hospital's DID, which the page shows and the server
itself confirms.

Deliberately not pytest. This is a script: it runs top to bottom, prints each
step as it happens, and exits non-zero on the first failure with the browser's
last known state reported. Run it through ``run_webui_inference_test.sh``, which
brings the stack up around it.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

import webui
from webui import (
    SHORT_WAIT,
    StepFailed,
    as_identity,
    asset_did,
    click,
    create_hand_signing_authority,
    create_system_authority,
    create_wallet,
    expect_statuses,
    expose,
    open_authority,
    open_own_asset,
    open_page,
    open_wallet,
    read_checklist,
    register_asset,
    run_flow,
    sign_as_authority,
    sign_as_wallet,
    visible,
    wait,
)

# ---------------------------------------------------------------- the tutorial
SCRIPT_OWNER = "data_user"
ISSUER = "vc_issuer"
HOSPITAL_A = "hospital_a"
HOSPITAL_B = "hospital_b"

SCRIPT_ASSET = "cohort_summary_script"
# The two sites of the federated round: different hospitals, different cohorts,
# each behind its own guardian, and not the same policies.
ASSET_A = "hospital_a_cohort"
ASSET_B = "hospital_b_cohort"

REVIEW_BOARD = "Code review board"
SYSTEM_AUTHORITY = "Session keys"
WALLET_KEYS = f"{SYSTEM_AUTHORITY} (wallet keys)"
WALLET_NAME = "researcher_wallet"

SCRIPT_PATH = os.environ.get("TUTORIAL_SCRIPT_PATH", "/tmp/inference_script.py")
COHORT_A_PATH = os.environ.get("TUTORIAL_COHORT_A_PATH", "/tmp/hospital_a_cohort.csv")
COHORT_B_PATH = os.environ.get("TUTORIAL_COHORT_B_PATH", "/tmp/hospital_b_cohort.csv")

SCRIPT_PORT = "7910"
GUARDIAN_PORT_A = "7900"
GUARDIAN_PORT_B = "7902"

# The disease the tutorial's script declares itself for.
ALLOWED_DISEASE = "MONDO:0005148"
# The institution the requester belongs to, which only Hospital B asks about.
ALLOWED_INSTITUTION = "did:example:best_university"

DS_CARD = "FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH"
IS_CARD = "FL-INFERENCE-INSTITUTION-SPECIFIC-RESTRICTION"

# A guardian answers /info before the FL client bundled with it has announced
# itself, so a site can be up for a few seconds before it is listed.
SITE_WAIT = int(os.environ.get("WEBUI_SITE_WAIT", "120"))

# The FL server the webapp is pointed at, asked directly for its DID -> client
# mapping so the page's account of it can be checked against the server's own.
FL_SERVER_URL = os.environ.get("FL_SERVER_URL", "http://localhost:7920")


def script_digest(path):
    """The digest naming a script, in the form the policy records."""
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


# ------------------------------------------------------------------- federated
READ_SITES = """
var rows = [];
document.querySelectorAll('#fl-sites-body tr').forEach(function (tr) {
    var check = tr.querySelector('[data-site-check]');
    rows.push({
        name: (tr.querySelector('[data-site-name]') || {}).textContent || '',
        did: (tr.querySelector('[data-site-did]') || {}).textContent || '',
        client: (tr.querySelector('[data-site-client]') || {}).textContent || '',
        state: (tr.querySelector('[data-site-state]') || {}).textContent || '',
        selectable: !!(check && !check.disabled),
    });
});
return {
    rows: rows,
    status: (document.getElementById('fl-server-status') || {}).textContent || '',
};
"""

SELECT_SITES = """
var wanted = arguments[0];
var problems = wanted.slice();          // anything still here was never selected
document.querySelectorAll('#fl-sites-body tr').forEach(function (tr) {
    var name = ((tr.querySelector('[data-site-name]') || {}).textContent || '').trim();
    var check = tr.querySelector('[data-site-check]');
    if (!check) { return; }
    var want = wanted.indexOf(name) >= 0;
    if (check.checked !== want) {
        check.click();   // the page tracks selection off the change event
    }
    // Only a box that ended up in the state we asked for counts as done: a
    // disabled one ignores the click, and a round that quietly dropped a site
    // would look like a passing round over fewer hospitals.
    if (want && check.checked) { problems.splice(problems.indexOf(name), 1); }
});
return problems;
"""

READ_ROUND = """
var sites = [];
document.querySelectorAll('#fl-result-body [data-site-row]').forEach(function (tr) {
    sites.push({
        name: tr.dataset.siteName,
        client: tr.dataset.siteClient || '',
        status: tr.dataset.siteStatus,
        text: (tr.querySelector('td:last-child') || {}).textContent || '',
    });
});
var agg = document.getElementById('fl-result-aggregate');
return { sites: sites, aggregate: agg ? agg.textContent : '' };
"""


def open_federated(runner):
    """Open the Federated page and wait for it to finish connecting."""
    open_page(runner, "/federated/")
    visible(runner.driver, "#fl-sites-empty, #fl-sites-table")
    wait(runner.driver, SHORT_WAIT).until(
        lambda d: "Connecting" not in d.execute_script(READ_SITES)["status"]
    )
    return runner.driver.execute_script(READ_SITES)


def await_sites(runner, names, timeout=SITE_WAIT):
    """Wait until every named site is listed and ready to take part.

    A guardian answers its readiness check before the FL client bundled with it
    has announced itself, so a freshly registered site can be a few seconds
    behind the asset that created it. Reconnecting is how the page re-reads the
    server, so that is what this does.
    """
    deadline = time.time() + timeout
    state = {"rows": [], "status": ""}
    while time.time() < deadline:
        state = open_federated(runner)
        ready = {
            row["name"].strip()
            for row in state["rows"]
            if row["selectable"] and "ready" in row["state"]
        }
        if set(names) <= ready:
            print(f"      sites: {sorted(ready)}", flush=True)
            return state
        webui.REC.tick()
        time.sleep(3)

    listed = [(r["name"].strip(), r["state"].strip()) for r in state["rows"]]
    raise StepFailed(
        f"sites {sorted(names)} were not all ready within {timeout}s; the page "
        f"lists {listed} ({state['status'].strip()})"
    )


def fl_server_mapping():
    """The FL server's own DID -> client mapping, for its connected clients."""
    with urllib.request.urlopen(f"{FL_SERVER_URL}/clients", timeout=10) as resp:
        clients = json.load(resp).get("clients") or []
    return {c["asset_did"]: c["client_id"] for c in clients if c.get("online")}


def expect_sites_matched(state, ports):
    """Each site is listed with the FL client beside its own guardian.

    ``ports`` maps a site's name to its guardian's port; the webapp names each
    FL client after its guardian's ``host:port``. The page's account is then
    checked against the FL server's own mapping, since that mapping -- not the
    page -- is what the server will address each site's job by. Returns
    ``{name: client_id}``.
    """
    mapping = fl_server_mapping()
    rows = {row["name"].strip(): row for row in state["rows"]}
    clients = {}
    for name, port in ports.items():
        did, client = rows[name]["did"].strip(), rows[name]["client"].strip()
        if not client.endswith(f":{port}"):
            raise StepFailed(
                f"{name} is listed with FL client {client!r}, not the one beside "
                f"its guardian on port {port}"
            )
        if mapping.get(did) != client:
            raise StepFailed(
                f"the page lists {name} ({did}) at FL client {client!r}, but the "
                f"FL server maps that DID to {mapping.get(did)!r}"
            )
        print(f"      {name}: {did} -> FL client {client}", flush=True)
        clients[name] = client
    return clients


def request_round(runner, *, sites, roles, checklists):
    """Select some sites on the Federated page and run one round over them.

    ``roles`` maps each role the selected sites' policies declare to the name of
    the wallet or script asset that fills it; it is checked against what the modal
    actually asks for, so a policy that changed its mind about its roles fails
    here rather than somewhere less legible. ``checklists`` maps each site to the
    ``{fact: status}`` its readiness checklist must show for those identities.

    Returns ``{"sites": [{name, status, text}], "aggregate": str}`` as the result
    panel states it.
    """
    open_federated(runner)
    missing = runner.driver.execute_script(SELECT_SITES, list(sites))
    if missing:
        raise StepFailed(
            f"could not select {missing} on the Federated page -- not listed, or "
            "listed but not available to take part"
        )

    click(runner.driver, "#fl-run")
    wait(runner.driver, SHORT_WAIT * 2).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "#fl-run-roles [data-role-select]")
    )
    asked = sorted(
        e.get_attribute("data-role")
        for e in runner.driver.find_elements(
            By.CSS_SELECTOR, "#fl-run-roles [data-role-select]"
        )
    )
    if asked != sorted(roles):
        raise StepFailed(
            f"expected the round to ask for {sorted(roles)}, it asks for {asked}"
        )
    for role, filled_by in roles.items():
        Select(visible(runner.driver, f"#fl-role-{role}")).select_by_visible_text(
            filled_by
        )

    # Each site's own checklist, for the identities chosen: every fact held, or
    # obtained on the way.
    wait(runner.driver, SHORT_WAIT * 2).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#fl-run-checklists .site-checklist")) == len(sites)
    )
    for site, expected in checklists.items():
        found = read_checklist(runner.driver, f"#fl-run-checklists .site-checklist[data-site-name='{site}']")
        expect_statuses(found, expected, site)
    wait(runner.driver, SHORT_WAIT).until(
        lambda d: d.find_element(By.CSS_SELECTOR, "#fl-run-submit").is_enabled()
    )

    click(runner.driver, "#fl-run-submit")
    steps = run_flow(runner.driver, ignore_step_errors=True)

    # A round that ran shows its result, refusals included. If no result panel
    # appears the flow failed as a whole rather than at a site, and the useful
    # thing to report is which step ended it -- not that an element never showed.
    try:
        visible(runner.driver, "#fl-result-body", SHORT_WAIT)
    except WebDriverException:
        errored = [s for s in steps if s["status"] == "error"]
        raise StepFailed(
            "the round produced no result; it ended at "
            + (
                f"{errored[-1]['step']!r}: {errored[-1]['detail']}"
                if errored
                else "no step that reported an error"
            )
        )
    round_result = runner.driver.execute_script(READ_ROUND)
    round_result["steps"] = steps
    for site in round_result["sites"]:
        print(f"      {site['name']}: {site['status']}", flush=True)
    print(f"      aggregate: {round_result['aggregate']}", flush=True)

    # A round reports a site whose policies refused rather than failing outright,
    # so a refusal would otherwise pass as "the round ran" over fewer hospitals.
    refused = {s["name"] for s in round_result["sites"] if s["status"] == "refused"}
    if refused:
        detail = "; ".join(
            f"{s['name']}: {s['text'][:120]}"
            for s in round_result["sites"]
            if s["status"] == "refused"
        )
        raise StepFailed(f"a site's policies refused the request -- {detail}")
    click(runner.driver, "[data-modal-close=fl-result-modal]")
    return round_result


def container_mounts(name):
    """The host paths bind-mounted into a running container, by container path."""
    out = subprocess.run(
        ["docker", "inspect", name, "--format", "{{json .Mounts}}"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise StepFailed(f"no container {name}: {out.stderr.strip()}")
    return {m["Destination"]: m["Source"] for m in json.loads(out.stdout) or []}


def expect_data_only_in_fl_client(port, data_path):
    """The guardian core holds no dataset; the FL client beside it holds this one."""
    core = f"pdo-inference-guardian-{port}"
    core_mounts = container_mounts(core)
    if core_mounts:
        raise StepFailed(f"guardian core {core} has data mounted: {core_mounts}")
    client_mounts = container_mounts(f"{core}-fl-client")
    if os.path.realpath(data_path) not in map(os.path.realpath, client_mounts.values()):
        raise StepFailed(
            f"the FL client beside {core} does not hold {data_path}: {client_mounts}"
        )
    print(f"      {core}: no data; its FL client holds {data_path}", flush=True)


def aggregate_of(round_result):
    try:
        return json.loads(round_result["aggregate"])
    except json.JSONDecodeError:
        raise StepFailed(
            f"the aggregate panel is not JSON: {round_result['aggregate'][:200]!r}"
        )


def expect_ran(round_result, names):
    """Assert exactly these sites ran the script and reported numbers."""
    ran = {s["name"] for s in round_result["sites"] if s["status"] == "complete"}
    if ran != set(names):
        raise StepFailed(f"expected {sorted(names)} to have run it, {sorted(ran)} did")


def expect_ran_at(round_result, clients):
    """Assert each site's job went to the FL client its DID is mapped to.

    ``clients`` is ``{name: client_id}`` as the Federated page listed them before
    the round. A capability is minted for one guardian, so a job that reached any
    other client could only have been refused there.
    """
    for site in round_result["sites"]:
        wanted = clients.get(site["name"])
        if site["client"] != wanted:
            raise StepFailed(
                f"{site['name']}'s job went to FL client {site['client']!r}, "
                f"but its DID is mapped to {wanted!r}"
            )
        print(f"      {site['name']}: run by FL client {site['client']}", flush=True)


# ---------------------------------------------------------------- the workflow
def run_workflow(runner):
    """The tutorial, in order, once.

    Every step below is a step a reader performs; nothing here explores a variant
    the tutorial does not describe.
    """
    state = {"digest": script_digest(SCRIPT_PATH)}
    sizes = {
        ASSET_A: os.path.getsize(COHORT_A_PATH),
        ASSET_B: os.path.getsize(COHORT_B_PATH),
    }
    print(f"\nscript digest: {state['digest']}", flush=True)
    print(f"cohort sizes : {sizes}", flush=True)

    # ------------------------------- Part 1: the script owner and their wallet
    runner.step(
        f"Become {SCRIPT_OWNER} (the script owner)",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )
    runner.step(
        "Publish the script behind a public guardian",
        lambda: register_asset(
            runner,
            name=SCRIPT_ASSET,
            path=SCRIPT_PATH,
            guardian_title="Public",
            port=SCRIPT_PORT,
        ),
    )

    def read_script_did():
        open_own_asset(runner, SCRIPT_ASSET)
        state["script_did"] = asset_did(runner.driver)
        print(f"      script DID: {state['script_did']}", flush=True)

    runner.step("Read the script's DID", read_script_did)

    def make_wallet():
        state["wallet_did"] = create_wallet(runner, WALLET_NAME)
        print(f"      wallet DID: {state['wallet_did']}", flush=True)

    runner.step("Create the requester's wallet", make_wallet)

    runner.step(
        "The wallet claims the script, signing with its own contract key",
        lambda: (
            open_wallet(runner, WALLET_NAME),
            sign_as_wallet(
                runner,
                fact="ScriptOwnershipCredential",
                about=state["script_did"],
                claims={"ownedBy": state["wallet_did"]},
            ),
        ),
    )

    # ------------------------------------------------ Part 2: the authorities
    runner.step(
        f"Become {ISSUER} (the trusted issuer)",
        lambda: as_identity(runner, ISSUER),
    )
    runner.step(
        "Create a hand-signing authority for the code and the requester",
        lambda: create_hand_signing_authority(
            runner,
            REVIEW_BOARD,
            facts=["ScriptHashCredential", "IntendedDataUseCredential", "AffiliationCredential"],
            checks="Reviews the code it is shown, and the requester's appointment.",
        ),
    )
    runner.step(
        "Sign the script's digest",
        lambda: (
            open_authority(runner, REVIEW_BOARD),
            sign_as_authority(
                runner,
                fact="ScriptHashCredential",
                about=state["script_did"],
                holder=state["script_did"],
                claims={"scriptHash": state["digest"]},
            ),
        ),
    )
    runner.step(
        "Sign the script's intended data use",
        lambda: sign_as_authority(
            runner,
            fact="IntendedDataUseCredential",
            about=state["script_did"],
            holder=state["script_did"],
            claims={"useOnlyFor": {"purposes": ["research"], "diseases": [ALLOWED_DISEASE]}},
        ),
    )
    runner.step(
        "Sign the requester's affiliation into their wallet",
        lambda: sign_as_authority(
            runner,
            fact="AffiliationCredential",
            about=state["wallet_did"],
            holder=state["wallet_did"],
            claims={"isMemberOf": ALLOWED_INSTITUTION, "typeOfMembership": "faculty"},
        ),
    )

    def make_system_authority():
        create_system_authority(runner, SYSTEM_AUTHORITY)
        # It comes with the wallet key authority FL-IS's wallet key rests on.
        webui.await_card_field(runner, WALLET_KEYS, "did", "authority")

    runner.step("Create a system authority, and its wallet key authority with it", make_system_authority)

    # ----------------------------------- Part 3: hospital A, one policy
    runner.step(
        f"Become {HOSPITAL_A} (the first dataset owner)",
        lambda: as_identity(runner, HOSPITAL_A),
    )
    runner.step(
        f"Publish {ASSET_A} behind its own inference guardian",
        lambda: register_asset(
            runner,
            name=ASSET_A,
            path=COHORT_A_PATH,
            guardian_title="Inference",
            port=GUARDIAN_PORT_A,
        ),
    )
    runner.step(
        "Hospital A exposes it under FL-DS, accepting the review board",
        lambda: expose(
            runner,
            asset=ASSET_A,
            cards=[DS_CARD],
            parameters={DS_CARD: {"allowedDiseases": [ALLOWED_DISEASE]}},
            authorities={
                "IntendedDataUseCredential": [REVIEW_BOARD],
                "ScriptHashCredential": [REVIEW_BOARD],
            },
        ),
    )

    # ------------------------ Part 4: hospital B, the same plus one about them
    runner.step(
        f"Become {HOSPITAL_B} (the second dataset owner)",
        lambda: as_identity(runner, HOSPITAL_B),
    )
    runner.step(
        f"Publish {ASSET_B} behind its own inference guardian",
        lambda: register_asset(
            runner,
            name=ASSET_B,
            path=COHORT_B_PATH,
            guardian_title="Inference",
            port=GUARDIAN_PORT_B,
        ),
    )
    runner.step(
        "Hospital B exposes it under BOTH policies",
        lambda: expose(
            runner,
            asset=ASSET_B,
            cards=[DS_CARD, IS_CARD],
            parameters={
                DS_CARD: {"allowedDiseases": [ALLOWED_DISEASE]},
                IS_CARD: {"allowedInstitutions": [ALLOWED_INSTITUTION]},
            },
            authorities={
                "IntendedDataUseCredential": [REVIEW_BOARD],
                "AffiliationCredential": [REVIEW_BOARD],
                "WalletVerifyingKeyCredential": [WALLET_KEYS],
                "ScriptHashCredential": [REVIEW_BOARD],
            },
        ),
    )

    # ------------------------------------------------ Part 5: the one round
    runner.step(
        f"Become {SCRIPT_OWNER} again to request the round",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def sites_connected():
        listed = await_sites(runner, [ASSET_A, ASSET_B])
        state["clients"] = expect_sites_matched(
            listed, {ASSET_A: GUARDIAN_PORT_A, ASSET_B: GUARDIAN_PORT_B}
        )

    runner.step(
        "Both hospitals show up on the Federated page, each by its FL client",
        sites_connected,
    )

    script_facts = {"IntendedDataUseCredential": "held", "ScriptHashCredential": "held"}

    def run_the_round():
        result = request_round(
            runner,
            sites=[ASSET_A, ASSET_B],
            # The union of what the two sites declared: A's modules want Script
            # only, B's want both.
            roles={"Script": SCRIPT_ASSET, "User": WALLET_NAME},
            checklists={
                ASSET_A: script_facts,
                ASSET_B: {
                    **script_facts,
                    "AffiliationCredential": "held",
                    "WalletVerifyingKeyCredential": "automatic",
                    "ScriptOwnershipCredential": "held",
                },
            },
        )
        expect_ran(result, [ASSET_A, ASSET_B])
        # The FL server matched each capability, by the DID it was minted for, to
        # the client holding that DID -- the one beside that hospital's guardian.
        expect_ran_at(result, state["clients"])
        aggregate = aggregate_of(result)
        if aggregate.get("sites") != 2:
            raise StepFailed(f"expected 2 sites in the aggregate: {aggregate}")
        # Proof that both hospitals really ran it over their own file: the totals
        # only add up if each guardian said yes and each FL client then ran over
        # the cohort it actually holds.
        expected = sizes[ASSET_A] + sizes[ASSET_B]
        if aggregate.get("total_samples") != expected:
            raise StepFailed(
                f"the aggregate covers {aggregate.get('total_samples')} bytes of "
                f"data, but the two cohorts are {expected} together -- the sites "
                "did not both run over their real files"
            )
        # And that the data is where the design says: with the FL clients.
        expect_data_only_in_fl_client(GUARDIAN_PORT_A, COHORT_A_PATH)
        expect_data_only_in_fl_client(GUARDIAN_PORT_B, COHORT_B_PATH)

    runner.step(
        "Run one round across both hospitals, and get an aggregate over both",
        run_the_round,
    )


if __name__ == "__main__":
    sys.exit(webui.main(run_workflow, (SCRIPT_PATH, COHORT_A_PATH, COHORT_B_PATH), __doc__))
