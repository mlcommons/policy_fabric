"""The browser side of the tutorial tests: the harness that runs, reports and
records the steps, and the page helpers every tutorial is made of.

A tutorial test is a script built on this module: ``main(run_workflow, files)``
brings up the display, the browser and the recorder, runs the workflow's steps in
order, and exits non-zero at the first failure with the browser's last known
state captured. The forms the helpers fill are the webapp's own; where a form is
generated from a JSON Schema (claims, a policy's parameters), ``fill_schema_form``
fills it field by field, by the schema's property names.
"""

import argparse
import os
import time
import traceback

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from recorder import SCREEN, NullRecorder, Recorder, VirtualDisplay

# A guardian deploy waits on a container coming up; a policy is several contract
# operations in a row; a round waits on every site's FL client claiming its job.
SHORT_WAIT = 30
FLOW_TIMEOUT = int(os.environ.get("WEBUI_FLOW_TIMEOUT", "600"))

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
    """The first element matching ``selector`` that is visible.

    Any match, not the first one: for a selector list such as "#empty, #table",
    selenium's own check looks only at whichever comes first in the DOM, and
    waits forever on a placeholder the page has already hidden.
    """
    return wait(driver, timeout).until(
        EC.visibility_of_any_elements_located((By.CSS_SELECTOR, selector))
    )[0]


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

    Assets, wallets and authorities are all listed as the same card -- a title, a DID,
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

    Creating a wallet or an authority is a plain form POST, so the list comes back
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


def create_wallet(runner, name):
    """Create a wallet from the Wallets page and return its DID."""
    open_page(runner, "/wallets/")
    click(runner.driver, "[data-modal-open=create-wallet-modal]")
    fill(runner.driver, "#wallet-name-input", name)
    click(runner.driver, "#create-wallet-modal button[type=submit]")
    return await_card_field(runner, name, "did", "wallet")


def open_wallet(runner, name):
    open_from_list(runner, "/wallets/", name, "[data-wallet-cid-url]", "wallet")



# ------------------------------------------------------------------ authorities
FILL_SCHEMA_FORM = """
function fill(container, values, path) {
    Object.keys(values).forEach(function (key) {
        var node = Array.prototype.filter.call(container.children, function (c) {
            return c.dataset && c.dataset.field === key;
        })[0];
        if (!node) { throw new Error('no field ' + path + key); }
        var value = values[key];
        if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
            fill(node, value, path + key + '.');
            return;
        }
        var input = node.querySelector('input, textarea, select');
        if (input.type === 'checkbox') {
            input.checked = !!value;
        } else {
            input.value = Array.isArray(value) ? value.join('\\n') : String(value);
        }
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
    });
}
var container = document.querySelector(arguments[0]);
if (!container) { throw new Error('no form at ' + arguments[0]); }
fill(container, arguments[1], '');
"""


def fill_schema_form(driver, selector, values):
    """Fill a form generated from a JSON Schema (static/js/schema_form.js).

    ``values`` has the shape of the object the form describes: nested objects
    fill nested fieldsets, lists fill one-per-line fields.
    """
    driver.execute_script(FILL_SCHEMA_FORM, selector, values)


def _create_authority(runner, name, kind, choose):
    """Create an authority from the Authorities page and return its DID; ``choose``
    fills what the kind asks for."""
    open_page(runner, "/authorities/")
    click(runner.driver, "[data-modal-open=create-authority-modal]")
    fill(runner.driver, "#authority-name", name)
    click(runner.driver, f"#create-authority-modal input[name=kind][value={kind}]")
    choose()
    click(runner.driver, "#create-authority-modal button[type=submit]")
    return await_card_field(runner, name, "did", "authority")


def create_hand_signing_authority(runner, name, *, facts, checks):
    """A hand-signing authority that attests ``facts`` after its own checks."""

    def choose():
        for fact in facts:
            click(runner.driver, f"#create-authority-modal input[name=facts][value={fact}]")
        fill(runner.driver, "#authority-checks", checks)

    return _create_authority(runner, name, "hand-signing", choose)


def create_rule_based_authority(runner, name, *, card):
    """A rule-based authority made from an authority card."""

    def choose():
        click(runner.driver, f"#create-authority-modal [data-template='{card}'] input")

    return _create_authority(runner, name, "rule-based", choose)


def create_system_authority(runner, name):
    """A session-key authority, with the wallet key authority it comes with."""
    return _create_authority(runner, name, "system", lambda: None)


def open_authority(runner, name):
    open_from_list(runner, "/authorities/", name, "[data-authority-cid-url]", "authority")


def _sign(runner, fact, about, claims, fill_holder):
    click(runner.driver, "[data-modal-open=sign-credential-modal]")
    visible(runner.driver, "#sign-credential-modal .modal")
    Select(visible(runner.driver, "#sign-fact")).select_by_value(fact)
    fill(runner.driver, "#sign-subject-did", about)
    fill_holder()
    fill_schema_form(runner.driver, "#sign-claims", claims)
    before = len(alerts(runner.driver))
    click(runner.driver, "#sign-credential-form button[type=submit]")

    wait(runner.driver, SHORT_WAIT * 4).until(lambda d: len(alerts(d)) > before)
    message = alerts(runner.driver)[-1]
    if message.startswith("Error"):
        raise StepFailed(f"signing {fact} failed: {message}")
    print(f"      {message}", flush=True)


def sign_as_authority(runner, *, fact, about, holder, claims):
    """On an open hand-signing authority, sign a credential about ``about`` and
    deliver it to the wallet ``holder``."""
    _sign(runner, fact, about, claims, lambda: fill(runner.driver, "#sign-holder-did", holder))


def sign_as_wallet(runner, *, fact, about, claims):
    """On an open wallet, sign a credential in the wallet's own name; it is stored
    in the contract ``about`` names."""
    _sign(runner, fact, about, claims, lambda: None)


def accept_authority(runner, fact, authority):
    """On an open trust panel, accept an authority for one fact, by its name."""
    driver = runner.driver
    row = f"#trust-panel tr[data-fact={fact}]"
    chosen = driver.execute_script(
        """
        var select = document.querySelector(arguments[0] + ' [data-accept-select]');
        if (!select) { return false; }
        for (var i = 0; i < select.options.length; i++) {
            if (select.options[i].textContent.indexOf(arguments[1] + ' ·') === 0) {
                select.value = select.options[i].value;
                select.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
        }
        return false;
        """,
        row,
        authority,
    )
    if not chosen:
        raise StepFailed(f"{authority!r} is not offered for {fact}")
    click(driver, f"{row} [data-action=accept]")
    wait(driver, SHORT_WAIT * 4).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, f"{row} .trust-entry[data-authority='{authority}']")
    )
    print(f"      {fact}: accepted {authority}", flush=True)


# ---------------------------------------------------------------------- expose
READ_REVIEW = "return (document.getElementById('expose-review') || {}).textContent || '';"


def expose(runner, *, asset, cards, parameters, authorities):
    """Expose an owned asset from its dashboard's Expose panel.

    ``cards`` are policy template names; ``parameters`` maps a card to the values
    of its parameter form; ``authorities`` maps each fact to the names of the
    authorities to accept for it. A fact preselected by the page is checked
    against the list rather than clicked again. Returns the review line.
    """
    open_own_asset(runner, asset)
    driver = runner.driver
    visible(driver, "#expose-panel")
    for card in cards:
        click(driver, f"#expose-cards .option-item[data-card='{card}'] input")
    for card, values in parameters.items():
        fill_schema_form(driver, f"#expose-parameters fieldset[data-parameters='{card}'] > div", values)

    for fact, names in authorities.items():
        for name in names:
            box = driver.find_elements(
                By.CSS_SELECTOR,
                f"#expose-authorities .fact-row[data-fact={fact}] "
                f".authority-option[data-authority='{name}'] input",
            )
            if not box:
                raise StepFailed(f"the panel does not offer {name!r} for {fact}")
            if not box[0].is_selected():
                box[0].click()

    review = driver.execute_script(READ_REVIEW)
    print(f"      {review}", flush=True)
    click(driver, "#expose-submit")
    run_flow(driver)
    return review


# ------------------------------------------------------------------ checklists
READ_CHECKLIST = """
var rows = {};
document.querySelectorAll(arguments[0] + ' tr[data-fact]').forEach(function (tr) {
    rows[tr.dataset.fact] = tr.dataset.status;
});
return rows;
"""


def read_checklist(driver, selector):
    """``{fact: status}`` of the readiness checklist rendered under ``selector``."""
    return driver.execute_script(READ_CHECKLIST, selector)


def expect_statuses(found, expected, where):
    if found != expected:
        raise StepFailed(f"{where}: expected the checklist to say {expected}, it says {found}")
    for fact, status in sorted(found.items()):
        print(f"      {fact}: {status}", flush=True)


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




def main(run_workflow, files=(), description=None):
    """Run a tutorial workflow in a recorded browser; returns the exit status."""
    global REC

    parser = argparse.ArgumentParser(description=description)
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

    for path in files:
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
