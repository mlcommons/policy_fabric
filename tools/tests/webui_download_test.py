"""The download tutorial, driven through the web UI.

Every click `docs/docs/tutorial.md` asks a reader to make, made by a browser instead,
in the same order:

* the requester signs in, which creates her wallet;
* the issuer creates a hand-signing registry office and session keys, and the office
  signs the requester's location and affiliation into her wallet;
* the owner publishes a dataset and exposes it under Geographical Restriction and
  Institution-Specific Restriction, whose graphs compose into one, with the allowed
  country and institution as their nodes' parameters;
* a card's popup, the dashboard and the Policies page draw their graphs, each fitting
  its panel at 1440px wide;
* the requester's checklist says she holds what the graph takes, and the download
  returns the data;
* once the owner allows only another country, the same request is refused.

What the run proves: two cards composed into one graph of policy components under one
Grant download, set with set_rego_policy and run by the contract, and a node's policy
data changed on its own.

Run it through ``run_webui_inference_test.sh -t download``, which brings the stack up
around it.
"""

import os
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

import webui
from webui import (
    SHORT_WAIT,
    StepFailed,
    as_identity,
    click,
    create_hand_signing_authority,
    create_system_authority,
    expect_statuses,
    expose,
    fill_schema_form,
    open_authority,
    open_own_asset,
    open_page,
    read_checklist,
    register_asset,
    run_flow,
    sign_as_authority,
    visible,
    wait,
)

REQUESTER = "data_user"
ISSUER = "vc_issuer"
OWNER = "data_owner"

REGISTRY = "University registry"
SESSION_KEYS = "Session keys"
UNIVERSITY = "did:example:best_university"

ASSET = "data1"
DATA_PATH = os.environ.get("TUTORIAL_DATA_PATH", "/tmp/asset_data.txt")
GUARDIAN_PORT = "7900"

CARDS = ["GEOGRAPHICAL-RESTRICTION", "INSTITUTION-SPECIFIC-RESTRICTION"]
NODES = ["geographical_restriction", "institution_specific_restriction", "grant_download"]


def requester_wallet(runner):
    """The DID and name of the wallet created for the requester when she first signed in."""
    open_page(runner, "/wallets/")
    did = runner.driver.execute_script(
        "var el = document.querySelector('.card .did-display'); return el ? el.textContent.trim() : '';"
    )
    if not did:
        raise StepFailed("the requester has no wallet")
    name = runner.driver.execute_script("return document.querySelector('.card h3').textContent.trim();")
    return did, name


def use_checklist(runner, wallet_name):
    """Open the Use modal on the asset, choose the wallet, and read the checklist."""
    open_page(runner, "/")
    click(runner.driver, f"[data-action=open-use][data-asset-name='{ASSET}']")
    Select(visible(runner.driver, "#use-wallet-User")).select_by_visible_text(wallet_name)
    wait(runner.driver, SHORT_WAIT * 2).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "#use-checklist tr[data-fact]")
    )
    return read_checklist(runner.driver, "#use-checklist")


# every drawn graph on the page that is wider than its panel: none should be, at 1440px
OVERFLOWING = """
return Array.from(document.querySelectorAll('.pf-panel'))
    .filter(function (p) { return p.offsetParent !== null && p.scrollWidth > p.clientWidth + 1; })
    .map(function (p) { return p.closest('[data-card], .modal, .card').textContent.trim().slice(0, 60); });
"""


def fits(runner, where):
    """At 1440px wide, every graph on the page fits its panel, once the graphs have refit."""
    runner.driver.set_window_size(1440, 900)
    try:
        wait(runner.driver, SHORT_WAIT).until(lambda d: not d.execute_script(OVERFLOWING))
    except Exception:
        raise StepFailed(f"on {where}, graphs wider than their panel at 1440px: "
                         f"{runner.driver.execute_script(OVERFLOWING)}")
    finally:
        runner.driver.set_window_size(*webui.SCREEN)


def submit_use(runner):
    wait(runner.driver, SHORT_WAIT).until(lambda d: d.find_element(By.CSS_SELECTOR, "#use-submit").is_enabled())
    click(runner.driver, "#use-submit")


def run_workflow(runner):
    state = {}

    # ------------------------------------------------ Part 1: the requester
    runner.step(f"Become {REQUESTER} (the requester)", lambda: as_identity(runner, REQUESTER))

    def read_wallet():
        state["wallet_did"], state["wallet_name"] = requester_wallet(runner)
        print(f"      wallet: {state['wallet_name']} {state['wallet_did']}", flush=True)

    runner.step("Read the requester's wallet DID", read_wallet)

    # ------------------------------------------------ Part 2: the issuer
    runner.step(f"Become {ISSUER} (the issuer)", lambda: as_identity(runner, ISSUER))
    runner.step(
        "Create the registry office",
        lambda: create_hand_signing_authority(
            runner, REGISTRY, facts=["LocationCredential", "AffiliationCredential"],
            checks="Checks enrolment records before signing.",
        ),
    )
    runner.step("Create the session-key authority", lambda: create_system_authority(runner, SESSION_KEYS))

    def sign_location_and_affiliation():
        wallet = state["wallet_did"]
        open_authority(runner, REGISTRY)
        sign_as_authority(runner, fact="LocationCredential", about=wallet, holder=wallet, claims={"locatedAt": {
            "street": "1 Main", "zipCode": "00000", "state": "MA", "country": "US"}})
        sign_as_authority(runner, fact="AffiliationCredential", about=wallet, holder=wallet,
                          claims={"isMemberOf": UNIVERSITY, "typeOfMembership": "member"})

    runner.step("The registry signs her location and affiliation into her wallet", sign_location_and_affiliation)

    # ------------------------------------------------ Part 3: the owner
    runner.step(f"Become {OWNER} (the dataset owner)", lambda: as_identity(runner, OWNER))
    runner.step(
        f"Publish {ASSET} behind a download guardian",
        lambda: register_asset(runner, name=ASSET, path=DATA_PATH, guardian_title="Download", port=GUARDIAN_PORT),
    )

    def the_cards_graph_first():
        open_own_asset(runner, ASSET)
        click(runner.driver, f"#expose-cards .option-item[data-card='{CARDS[0]}'] button")
        visible(runner.driver, "#card-detail-modal [data-card-panel=graph].active .pf-graph .vc.cap")
        tabs = runner.driver.execute_script(
            "return Array.from(document.querySelectorAll('#card-detail-modal [data-card-tab]')).map(b => b.textContent);"
        )
        if tabs != ["Graph", "Policy card", "Rego"]:
            raise StepFailed(f"the popup's tabs are {tabs}")
        if "modal-wide" not in runner.driver.find_element(By.CSS_SELECTOR, "#card-detail-modal .modal").get_attribute("class"):
            raise StepFailed("the popup does not widen for its graph")
        fits(runner, "the card popup")
        click(runner.driver, "[data-modal-close=card-detail-modal]")

    runner.step("A card's popup opens on its graph", the_cards_graph_first)

    def expose_both():
        review = expose(
            runner,
            asset=ASSET,
            cards=CARDS,
            parameters={
                "geographical_restriction": {"allowedCountries": ["US"]},
                "institution_specific_restriction": {"allowedInstitutions": [UNIVERSITY]},
            },
            authorities={
                "LocationCredential": [REGISTRY],
                "AffiliationCredential": [REGISTRY],
                "publicKeyCredential": [SESSION_KEYS],
            },
        )
        if review != "Requesters will present one of: Affiliation + Location + Session key.":
            raise StepFailed(f"the review line does not list the one way to meet the graph: {review}")

    runner.step("Expose it under GS and IS, composed into one graph", expose_both)

    def graph_on_the_dashboard():
        open_own_asset(runner, ASSET)
        visible(runner.driver, "#asset-policy-graph")
        wait(runner.driver, SHORT_WAIT).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#asset-policy-graph .pcw")) == len(NODES)
        )
        names = runner.driver.execute_script(
            "return Array.from(document.querySelectorAll('#asset-policy-graph .pc-nm')).map(e => e.textContent);"
        )
        print(f"      components: {', '.join(names)}", flush=True)
        if not runner.driver.find_elements(By.CSS_SELECTOR, "#asset-policy-graph .vc.cap"):
            raise StepFailed("the dashboard draws no capability")
        visible(runner.driver, "#node-data-forms fieldset[data-parameters=geographical_restriction]")
        fits(runner, "the dashboard")

    runner.step("The dashboard draws the composed graph", graph_on_the_dashboard)

    def every_card_on_the_policies_page():
        open_page(runner, "/policies/")
        wait(runner.driver, SHORT_WAIT).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, ".policy-card .pf-graph .vc.cap")) == 23
        )
        fits(runner, "the Policies page")

    runner.step("The Policies page draws every card", every_card_on_the_policies_page)

    # ------------------------------------------------ Part 4: the requester downloads
    runner.step(f"Become {REQUESTER} again", lambda: as_identity(runner, REQUESTER))

    def download():
        found = use_checklist(runner, state["wallet_name"])
        expect_statuses(found, {"LocationCredential": "held", "AffiliationCredential": "held",
                                "publicKeyCredential": "automatic"}, ASSET)
        submit_use(runner)
        run_flow(runner.driver)
        output = visible(runner.driver, "#use-result-output", SHORT_WAIT * 2).text
        if "The eagle lands at midnight." not in output:
            raise StepFailed(f"unexpected data: {output!r}")
        print(f"      data: {output.strip()}", flush=True)

    runner.step("The graph qualifies her, and the data comes back", download)

    # ------------------------------------------------ one node's policy data
    runner.step(f"Become {OWNER} again", lambda: as_identity(runner, OWNER))

    def allow_another_country():
        open_own_asset(runner, ASSET)
        fill_schema_form(runner.driver, "#node-data-forms fieldset[data-parameters=geographical_restriction] > div",
                         {"allowedCountries": ["CA"]})
        click(runner.driver, "#node-data-forms fieldset[data-parameters=geographical_restriction] .btn-primary")
        wait(runner.driver, SHORT_WAIT * 2).until(
            lambda d: "updated" in d.execute_script("return document.body.textContent;")
        )

    runner.step("She allows only another country on the geographical restriction", allow_another_country)
    runner.step(f"Become {REQUESTER} for the last time", lambda: as_identity(runner, REQUESTER))

    def refused():
        use_checklist(runner, state["wallet_name"])
        submit_use(runner)
        run_flow(runner.driver, expect_error=True)
        text = runner.driver.execute_script("return document.body.textContent;")
        if "the root issued no capability" not in text:
            raise StepFailed("the download was not refused by the graph")

    runner.step("The same request is now refused", refused)


if __name__ == "__main__":
    sys.exit(webui.main(run_workflow, (DATA_PATH,), __doc__))
