"""The federated inference tutorial, driven through the web UI.

Every click `docs/docs/tutorial_inference.md` asks a reader to make, made by a
browser instead, in the same order and with nothing added:

* the script owner publishes their code behind a public guardian, gets a wallet,
  and has that wallet claim the script;
* the trusted issuer vouches for the code (digest, declared diseases), for the
  requester (institution), and creates the session-key issuer that will bind a
  fresh key to the requester's wallet;
* **Hospital A** puts its cohort behind an inference guardian under **FL-DS**;
* **Hospital B** puts its own cohort behind its own guardian under **FL-DS and
  FL-IS together** -- two subpolicies of one policy agent, both of which must
  allow;
* the script owner runs **one round** across both, filling the union of the roles
  the two sites ask for, and gets per-site metrics and one aggregate back.

What the run proves, beyond "it works": the aggregate's ``total_samples`` is the
sum of the two cohorts' real sizes, so it only adds up if each guardian released
the file it actually holds; and the Use form asks for exactly ``Script`` and
``User``, which is the union of what A and B declared and not what either asked
for alone.

Deliberately not pytest. This is a script: it runs top to bottom, prints each
step as it happens, and exits non-zero on the first failure with the browser's
last known state reported. Run it through ``run_webui_inference_test.sh``, which
brings the stack up around it.

It also records itself. The browser draws on a virtual display and ffmpeg records
that display for the whole run, captioned with the step it is on -- see
``recorder.py``. A headless run is otherwise invisible.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from recorder import SCREEN, NullRecorder, Recorder, VirtualDisplay

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

ISSUER_NAME = "code review board"
SESSION_KEY_ISSUER = "session keys"
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

DS_POLICY_NAME = "FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH"
IS_POLICY_NAME = "FL-INFERENCE-INSTITUTION-SPECIFIC-RESTRICTION"

# A guardian deploy waits on a container coming up; a policy is several contract
# operations in a row; a round waits on every site's FL client claiming its job.
SHORT_WAIT = 30
FLOW_TIMEOUT = int(os.environ.get("WEBUI_FLOW_TIMEOUT", "600"))
# A guardian answers /info before the FL client bundled with it has announced
# itself, so a site can be up for a few seconds before it is listed.
SITE_WAIT = int(os.environ.get("WEBUI_SITE_WAIT", "120"))

# Replaces window.alert with an on-page toast. The webapp reports everything
# through alert(), which in a driven browser is a modal that blocks the page and
# is invisible in the recording. The shim is display-only -- the same messages,
# in the same order, kept where both the video and the test can read them.
ALERT_SHIM = """
(function () {
    if (window.__pdoAlertShim) { return; }
    window.__pdoAlertShim = [];
    function toast(text) {
        var el = document.getElementById('__pdo_toast__');
        if (!el) {
            el = document.createElement('div');
            el.id = '__pdo_toast__';
            el.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483646;'
                + 'pointer-events:none;max-width:44rem;display:flex;flex-direction:column;'
                + 'gap:6px;align-items:flex-end;';
            (document.body || document.documentElement).appendChild(el);
        }
        var line = document.createElement('div');
        var bad = /^Error/i.test(text);
        line.style.cssText = 'background:' + (bad ? '#7f1d1d' : '#14532d') + ';color:#fff;'
            + 'font:500 15px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
            + 'padding:9px 14px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,.35);';
        line.textContent = text;
        el.appendChild(line);
        setTimeout(function () { line.remove(); }, 6000);
    }
    window.alert = function (text) {
        text = String(text);
        window.__pdoAlertShim.push(text);
        try { toast(text); } catch (e) { /* before <body> exists */ }
    };
})();
"""

# One poll of a running flow: the steps the progress modal is showing, and
# whether it has finished. Read in one call so a re-render cannot hand back a
# stale element mid-read.
FLOW_STATE = """
var steps = [];
document.querySelectorAll('#progress-steps li').forEach(function (row) {
    steps.push({
        step: row.dataset.step,
        status: row.dataset.status,
        label: (row.querySelector('.progress-step-label') || {}).textContent || '',
        detail: (row.querySelector('.progress-step-detail') || {}).textContent || '',
    });
});
var close = document.getElementById('progress-close');
return {
    steps: steps,
    finished: !!(close && close.style.display !== 'none'),
    title: (document.getElementById('progress-title') || {}).textContent || '',
};
"""

REC = NullRecorder()


class StepFailed(Exception):
    pass


# ---------------------------------------------------------------- the harness
class Runner:
    """Runs the steps, reports them, and stops at the first failure."""

    def __init__(self, driver, base_url, artifacts):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.artifacts = artifacts
        self.passed = 0
        self.failed = None
        self.started = time.time()

    def url(self, path):
        return self.base_url + path

    def step(self, name, fn):
        if self.failed:
            return
        print(f"\n=== {name} ", flush=True)
        began = time.time()
        REC.caption(f"{self.passed + 1:02d}  {name}")
        try:
            fn()
        except Exception as error:
            self.failed = name
            print(
                f"    FAILED after {time.time() - began:.1f}s: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            REC.caption(f"{self.passed + 1:02d}  {name} -- FAILED")
            self._capture(name)
            traceback.print_exc()
        else:
            self.passed += 1
            print(f"    ok ({time.time() - began:.1f}s)", flush=True)

    def _capture(self, name):
        """A failure in a browser is invisible unless something records it."""
        slug = "".join(c if c.isalnum() else "_" for c in name)[:60]
        try:
            os.makedirs(self.artifacts, exist_ok=True)
            shot = os.path.join(self.artifacts, f"{slug}.png")
            self.driver.save_screenshot(shot)
            html = os.path.join(self.artifacts, f"{slug}.html")
            with open(html, "w") as f:
                f.write(self.driver.page_source)
            print(f"    url  : {self.driver.current_url}", flush=True)
            print(f"    shot : {shot}", flush=True)
            print(f"    html : {html}", flush=True)
        except WebDriverException as error:
            print(f"    (could not capture page state: {error})", flush=True)

    def report(self):
        took = time.time() - self.started
        print("\n" + "=" * 60, flush=True)
        if self.failed:
            print(f"FAILED at: {self.failed}", flush=True)
            print(f"{self.passed} steps passed before it, {took:.0f}s elapsed", flush=True)
            return 1
        print(f"PASSED: {self.passed} steps in {took:.0f}s", flush=True)
        return 0


# ---------------------------------------------------------------- page helpers
def wait(driver, timeout=SHORT_WAIT):
    return WebDriverWait(driver, timeout)


def visible(driver, selector, timeout=SHORT_WAIT):
    return wait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )


def click(driver, selector, timeout=SHORT_WAIT):
    element = wait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    element.click()
    return element


def fill(driver, selector, value, timeout=SHORT_WAIT):
    element = visible(driver, selector, timeout)
    element.clear()
    element.send_keys(value)
    return element


def set_value(driver, selector, value):
    """Put a value into a field without typing it.

    A JSON blob typed character by character is slow and, in a textarea the page
    reformats as you go, unreliable. The input/change events the page listens for
    are dispatched by hand.
    """
    driver.execute_script(
        """
        var el = document.querySelector(arguments[0]);
        if (!el) { throw new Error('no element for ' + arguments[0]); }
        el.value = arguments[1];
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        selector,
        value,
    )


def open_page(runner, path):
    runner.driver.get(runner.url(path))
    visible(runner.driver, "nav.navbar")


def alerts(driver):
    return driver.execute_script("return window.__pdoAlertShim || [];")


def run_flow(driver, timeout=FLOW_TIMEOUT, expect_error=False, ignore_step_errors=False):
    """Wait out a streaming flow and return the steps the modal showed.

    Every multi-step action in this webapp -- provisioning, registering,
    exposing, running a round -- reports through the same progress modal, so one
    waiter covers all of them. Raises unless the outcome is the one asked for.

    ``ignore_step_errors`` is for the federated round, where a step can fail
    without the flow failing: a site refusing is one of the outcomes the round
    exists to report, and the caller checks which sites those were.
    """
    started_at = driver.current_url
    deadline = time.time() + timeout
    state = {"steps": [], "finished": False, "title": ""}
    while time.time() < deadline:
        REC.tick()
        try:
            state = driver.execute_script(FLOW_STATE)
            here = driver.current_url
        except WebDriverException:
            # Mid-navigation: the flow finished and redirected.
            time.sleep(1.0)
            return []
        if state["finished"]:
            break
        # The flow's own terminal redirect landed before this loop saw it, so
        # there is nothing left on this page to wait for.
        if here != started_at and not state["steps"]:
            time.sleep(0.5)
            return []
        time.sleep(0.4)
    else:
        shown = ", ".join(f"{s['step']}={s['status']}" for s in state["steps"])
        raise StepFailed(f"flow did not finish within {timeout}s (steps: {shown})")

    errored = [s for s in state["steps"] if s["status"] == "error"]
    for s in state["steps"]:
        print(f"      [{s['status']:>7}] {s['label']} {s['detail']}", flush=True)

    if not ignore_step_errors:
        if expect_error and not errored:
            raise StepFailed("the flow was expected to fail, and did not")
        if errored and not expect_error:
            first = errored[0]
            raise StepFailed(f"step {first['step']!r} failed: {first['detail']}")

    # A flow that redirects does so shortly after it reports done. Let that land
    # here rather than under whatever the next step has already navigated to.
    if not errored:
        time.sleep(1.5)
    return state["steps"]


def as_identity(runner, name):
    """Switch the client's identity, provisioning it the first time."""
    open_page(runner, "/")
    select = Select(visible(runner.driver, "#nav-identity-select"))
    if (select.first_selected_option.get_attribute("value") or "") == name:
        return
    select.select_by_value(name)
    run_flow(runner.driver)

    def is_current(d):
        # The page is reloading underneath this, so anything read from it can be
        # gone by the time it is read.
        try:
            element = d.find_element(By.CSS_SELECTOR, "#nav-identity-select")
            return Select(element).first_selected_option.get_attribute("value") == name
        except WebDriverException:
            return False

    wait(runner.driver, SHORT_WAIT).until(is_current)


def register_asset(runner, *, name, path, guardian_title, port):
    """Fill in the registration form and wait for the guardian behind it."""
    open_page(runner, "/assets/setup/")
    fill(runner.driver, "#id_name", name)
    fill(runner.driver, "#id_data_source", path)
    Select(visible(runner.driver, "#id_guardian_type")).select_by_visible_text(
        guardian_title
    )
    Select(visible(runner.driver, "#id_serve_on")).select_by_value("0.0.0.0")
    fill(runner.driver, "#id_port", port)
    click(runner.driver, "form[data-progress-url] button[type=submit]")
    run_flow(runner.driver)


def card_field(driver, name, part):
    """Read one field off the card with this title on a list page.

    Assets, wallets and issuers are all listed as the same card -- a title, a DID,
    and an Open link -- so one reader serves all three. ``part`` is "did" or
    "href"; an empty string means there is no such card.
    """
    return driver.execute_script(
        """
        var wanted = arguments[0], part = arguments[1], found = '';
        document.querySelectorAll('.card').forEach(function (card) {
            var title = card.querySelector('h3');
            if (!title || title.textContent.trim() !== wanted) { return; }
            var el = card.querySelector(part === 'did' ? '.did-display' : 'a.btn');
            if (el) {
                found = part === 'did' ? el.textContent.trim() : el.getAttribute('href');
            }
        });
        return found;
        """,
        name,
        part,
    )


def await_card_field(runner, name, part, what):
    """Wait for a card to appear on the current list page, then read a field.

    Creating a wallet or an issuer is a plain form POST, so the list comes back
    with the new card on it -- but the contract work happens first, and an
    external key authority makes two contracts before it answers.
    """
    try:
        wait(runner.driver, SHORT_WAIT * 8).until(
            lambda d: card_field(d, name, part)
        )
    except WebDriverException:
        raise StepFailed(f"no {what} card named {name!r} appeared")
    return card_field(runner.driver, name, part)


def open_from_list(runner, list_path, name, marker, what):
    """Open the detail page of something listed at ``list_path``."""
    open_page(runner, list_path)
    href = card_field(runner.driver, name, "href")
    if not href:
        raise StepFailed(f"no {what} card named {name!r}")
    runner.driver.get(runner.url(href))
    visible(runner.driver, marker)


def open_own_asset(runner, name):
    """Open the dashboard of an asset this identity owns, from the asset list."""
    open_from_list(runner, "/", name, "[data-asset-cid-url]", "owned asset")


def asset_did(driver):
    return visible(driver, "[data-asset-cid-url]").get_attribute("data-asset-did")


def create_issuer(runner, name, kind="manual"):
    """Create an issuer object from the Issuers page and return its DID."""
    open_page(runner, "/issuers/")
    click(runner.driver, "[data-modal-open=create-issuer-modal]")
    fill(runner.driver, "#issuer-name-input", name)
    click(runner.driver, f"#create-issuer-modal input[value={kind}]")
    click(runner.driver, "#create-issuer-modal button[type=submit]")
    return await_card_field(runner, name, "did", "issuer")


def open_issuer(runner, name):
    open_from_list(runner, "/issuers/", name, "[data-issuer-cid-url]", "issuer")


def create_wallet(runner, name):
    """Create a wallet from the Wallets page and return its DID."""
    open_page(runner, "/wallets/")
    click(runner.driver, "[data-modal-open=create-wallet-modal]")
    fill(runner.driver, "#wallet-name-input", name)
    click(runner.driver, "#create-wallet-modal button[type=submit]")
    return await_card_field(runner, name, "did", "wallet")


def open_wallet(runner, name):
    open_from_list(runner, "/wallets/", name, "[data-wallet-cid-url]", "wallet")


def sign_credential(runner, *, template, subject_did, claims):
    """Sign one credential from whichever signer's page is open.

    A manual issuer and a wallet present the same form -- what differs is the key
    behind it, which the server picks and the browser never sees.
    """
    click(runner.driver, "[data-modal-open=sign-credential-modal]")
    visible(runner.driver, "#sign-credential-modal .modal")
    Select(visible(runner.driver, "#sign-template-select")).select_by_value(template)
    fill(runner.driver, "#sign-subject-did", subject_did)
    set_value(runner.driver, "#sign-claims-input", json.dumps(claims, indent=2))
    before = len(alerts(runner.driver))
    click(runner.driver, "#sign-credential-form button[type=submit]")

    wait(runner.driver, SHORT_WAIT * 4).until(
        lambda d: len(alerts(d)) > before
    )
    message = alerts(runner.driver)[-1]
    if message.startswith("Error"):
        raise StepFailed(f"signing {template} failed: {message}")
    print(f"      {message}", flush=True)


def script_digest(path):
    """The digest naming a script, in the form the policy records."""
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def expose_asset(runner, *, asset, policies, policy_data, issuers):
    """Attach policies to an owned asset and trust the issuers they read.

    ``policies`` is a list of policy names: an asset may carry several, each
    becoming a subpolicy of its one policy agent, all of which must allow. The
    policy data is set *after* they are all checked, because checking one
    rewrites that box with the union of the checked policies' schemas.

    ``issuers`` is a list of ``(did, [credential_type, ...])``; each becomes one
    box in the expose form's trusted-issuer section.
    """
    open_own_asset(runner, asset)
    click(runner.driver, "[data-modal-open=expose-modal]")
    visible(runner.driver, "#expose-modal .modal")

    for policy in policies:
        checked = runner.driver.execute_script(
            """
            var wanted = arguments[0];
            var hit = null;
            document.querySelectorAll('#id_policy_templates .checkbox-item').forEach(
                function (row) {
                    var label = row.querySelector('label');
                    if (label && label.textContent.trim() === wanted) {
                        hit = row.querySelector('input[name=policy_templates]');
                    }
                });
            if (!hit) { return false; }
            hit.click();
            return true;
            """,
            policy,
        )
        if not checked:
            raise StepFailed(f"the expose form does not offer a policy named {policy!r}")

    set_value(runner.driver, "#id_policy_data", json.dumps(policy_data, indent=2))

    for did, types in issuers:
        click(runner.driver, "#expose-add-issuer")
        runner.driver.execute_script(
            """
            var did = arguments[0];
            var types = arguments[1];
            var boxes = document.querySelectorAll(
                '#expose-trusted-issuers .trusted-issuer-box');
            var box = boxes[boxes.length - 1];
            if (!box) { throw new Error('no trusted-issuer box was added'); }
            box.querySelector('.ti-did').value = did;
            var missing = [];
            types.forEach(function (t) {
                var hit = null;
                box.querySelectorAll('.ti-types .checkbox-item').forEach(function (row) {
                    if (row.textContent.trim() === t) { hit = row.querySelector('input'); }
                });
                if (hit) { hit.checked = true; } else { missing.push(t); }
            });
            if (missing.length) {
                throw new Error('credential types not offered: ' + missing.join(', '));
            }
            """,
            did,
            types,
        )

    click(runner.driver, "#expose-form button[type=submit]")
    run_flow(runner.driver)


# ------------------------------------------------------------------- federated
READ_SITES = """
var rows = [];
document.querySelectorAll('#fl-sites-body tr').forEach(function (tr) {
    var check = tr.querySelector('[data-site-check]');
    rows.push({
        name: (tr.querySelector('[data-site-name]') || {}).textContent || '',
        did: (tr.querySelector('[data-site-did]') || {}).textContent || '',
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
        REC.tick()
        time.sleep(3)

    listed = [(r["name"].strip(), r["state"].strip()) for r in state["rows"]]
    raise StepFailed(
        f"sites {sorted(names)} were not all ready within {timeout}s; the page "
        f"lists {listed} ({state['status'].strip()})"
    )


def request_round(runner, *, sites, roles):
    """Select some sites on the Federated page and run one round over them.

    ``roles`` maps each role the selected sites' policies declare to the name of
    the wallet or script asset that fills it; it is checked against what the modal
    actually asks for, so a policy that changed its mind about its roles fails
    here rather than somewhere less legible.

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
            sign_credential(
                runner,
                template="ScriptOwnershipCredential",
                subject_did=state["script_did"],
                claims={"ownedBy": state["wallet_did"]},
            ),
        ),
    )

    # ------------------------------------------------ Part 2: trusted issuer
    runner.step(
        f"Become {ISSUER} (the trusted issuer)",
        lambda: as_identity(runner, ISSUER),
    )

    def make_issuer():
        state["issuer_did"] = create_issuer(runner, ISSUER_NAME)
        print(f"      issuer DID: {state['issuer_did']}", flush=True)

    runner.step("Create the manual issuer object", make_issuer)

    runner.step(
        "Sign the ScriptHashCredential about the script",
        lambda: (
            open_issuer(runner, ISSUER_NAME),
            sign_credential(
                runner,
                template="ScriptHashCredential",
                subject_did=state["script_did"],
                claims={"scriptHash": state["digest"]},
            ),
        ),
    )
    runner.step(
        "Sign the IntendedDataUseCredential about the script",
        lambda: sign_credential(
            runner,
            template="IntendedDataUseCredential",
            subject_did=state["script_did"],
            claims={
                "useOnlyFor": {
                    "purposes": ["research"],
                    "diseases": [ALLOWED_DISEASE],
                }
            },
        ),
    )
    runner.step(
        "Sign the AffiliationCredential into the requester's wallet",
        lambda: sign_credential(
            runner,
            template="AffiliationCredential",
            subject_did=state["wallet_did"],
            claims={
                "isMemberOf": ALLOWED_INSTITUTION,
                "typeOfMembership": "faculty",
            },
        ),
    )

    def make_session_key_issuer():
        state["binding_did"] = create_issuer(
            runner, SESSION_KEY_ISSUER, kind="external_key_authority"
        )
        # Creating it also created the wallet key authority that attests a
        # wallet's ledger-registered key for it; FL-IS has to trust both.
        state["wallet_key_did"] = await_card_field(
            runner, f"{SESSION_KEY_ISSUER} (wallet keys)", "did", "issuer"
        )
        print(f"      session key issuer DID: {state['binding_did']}", flush=True)
        print(f"      wallet key issuer DID : {state['wallet_key_did']}", flush=True)

    runner.step(
        "Create the session-key issuer, and its wallet key authority with it",
        make_session_key_issuer,
    )

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
        "Hospital A attaches FL-DS, and trusts the issuer it reads",
        lambda: expose_asset(
            runner,
            asset=ASSET_A,
            policies=[DS_POLICY_NAME],
            policy_data={"allowedDiseases": [ALLOWED_DISEASE]},
            issuers=[
                (
                    state["issuer_did"],
                    ["ScriptHashCredential", "IntendedDataUseCredential"],
                )
            ],
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
        "Hospital B attaches BOTH policies, and trusts all three issuers",
        lambda: expose_asset(
            runner,
            asset=ASSET_B,
            policies=[DS_POLICY_NAME, IS_POLICY_NAME],
            policy_data={
                "allowedDiseases": [ALLOWED_DISEASE],
                "allowedInstitutions": [ALLOWED_INSTITUTION],
            },
            issuers=[
                (
                    state["issuer_did"],
                    [
                        "ScriptHashCredential",
                        "IntendedDataUseCredential",
                        "AffiliationCredential",
                    ],
                ),
                (state["binding_did"], ["publicKeyCredential"]),
                (state["wallet_key_did"], ["WalletVerifyingKeyCredential"]),
            ],
        ),
    )

    # ------------------------------------------------ Part 5: the one round
    runner.step(
        f"Become {SCRIPT_OWNER} again to request the round",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )
    runner.step(
        "Both hospitals show up on the Federated page as connected sites",
        lambda: await_sites(runner, [ASSET_A, ASSET_B]),
    )

    def run_the_round():
        result = request_round(
            runner,
            sites=[ASSET_A, ASSET_B],
            # The union of what the two sites declared: A's FL-DS wants Script
            # only, B's FL-DS + FL-IS want both. request_round checks the modal
            # asks for exactly this, so a policy that changed its mind about its
            # roles fails here rather than somewhere less legible.
            roles={"Script": SCRIPT_ASSET, "User": WALLET_NAME},
        )
        expect_ran(result, [ASSET_A, ASSET_B])
        aggregate = aggregate_of(result)
        if aggregate.get("sites") != 2:
            raise StepFailed(f"expected 2 sites in the aggregate: {aggregate}")
        # Proof that both hospitals really ran it over their own file: the totals
        # only add up if each guardian released the cohort it actually holds.
        expected = sizes[ASSET_A] + sizes[ASSET_B]
        if aggregate.get("total_samples") != expected:
            raise StepFailed(
                f"the aggregate covers {aggregate.get('total_samples')} bytes of "
                f"data, but the two cohorts are {expected} together -- the sites "
                "did not both run over their real files"
            )

    runner.step(
        "Run one round across both hospitals, and get an aggregate over both",
        run_the_round,
    )


# ---------------------------------------------------------------- entry point
def build_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    # Chrome will not start as root, and a small /dev/shm makes it flaky.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    # Filling the display it was given, so the recording is the browser and
    # nothing else.
    options.add_argument("--window-position=0,0")
    options.add_argument(f"--window-size={SCREEN[0]},{SCREEN[1]}")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(120)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": ALERT_SHIM}
        )
    except WebDriverException:
        print("    (could not install the alert shim; alerts will block)", flush=True)
    return driver


def open_display(args, parser):
    """Where the browser draws, and whether that is somewhere recordable."""
    if args.headed:
        if not os.environ.get("DISPLAY"):
            parser.error("--headed needs a DISPLAY; drop it to record instead")
        return None, False
    if args.no_record:
        return None, True

    display = VirtualDisplay()
    try:
        display.start()
    except RuntimeError as error:
        print(f"Not recording: {error}", flush=True)
        return None, True
    return display, False


def main():
    global REC

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--headed", action="store_true",
        help="watch it live on this machine's screen, and record nothing",
    )
    parser.add_argument(
        "--artifacts",
        default=os.environ.get("WEBUI_ARTIFACTS", "/tmp/pdo_webui_artifacts"),
    )
    parser.add_argument("--no-record", action="store_true", help="skip the video")
    parser.add_argument("--fps", type=int, default=int(os.environ.get("WEBUI_FPS", "10")))
    args = parser.parse_args()

    for path in (SCRIPT_PATH, COHORT_A_PATH, COHORT_B_PATH):
        if not os.path.isfile(path):
            parser.error(f"missing tutorial file {path}; run tools/make_tutorial_files.sh")

    display, headless = open_display(args, parser)
    driver = build_driver(headless=headless)
    runner = Runner(driver, f"http://{args.host}:{args.port}", args.artifacts)

    video = None
    if display:
        REC = Recorder(
            driver, display, os.path.join(args.artifacts, "run.mp4"), fps=args.fps
        )
        REC.start()

    try:
        run_workflow(runner)
    finally:
        # Stopped before the browser goes: the last thing that happened should
        # be in the video rather than the moment it disappeared.
        video = REC.stop()
        driver.quit()
        if display:
            display.stop()

    if video:
        print(f"\nvideo: {video}", flush=True)
    return runner.report()


if __name__ == "__main__":
    sys.exit(main())
