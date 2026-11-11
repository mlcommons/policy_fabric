"""The ethics approval tutorial, driven through the web UI.

Every click `docs/docs/tutorial_irb.md` asks a reader to make, made by a browser
instead, in the same order:

* the offices create a records office, an ethics registry and the IRB office
  (hand-signing), and session keys (system);
* the owner exposes a dataset under the ethics approval card, whose graph joins the
  chain itself: the records office accepted for the team, the PI's project ownership
  and the affiliation, the ethics registry for the approval, the accreditation and the
  project's intended use, and the IRB office for an IRB clearance, which the graph also
  accepts in place of the chain;
* the requester's checklist, while she holds nothing, shows the shortest way to
  qualify: ask the IRB office for a clearance and the ethics registry for the
  project's intended use;
* the offices deliver the chain -- credentials about her, her PI, the project and the
  approving committee -- to her wallet;
* her checklist now shows the whole chain held, and the download returns the data:
  the graph's components joined the chain into an IRB clearance of their own, and she
  never needed one from the IRB office.

What the run proves: one card whose graph walks a chain of credentials about four
subjects, a credential that can stand in for part of it, and a checklist that says
which way the requester can qualify before anything is submitted.

Run it through ``run_webui_inference_test.sh -t irb``, which brings the stack up
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
    open_authority,
    open_page,
    open_wallet,
    read_checklist,
    register_asset,
    run_flow,
    sign_as_authority,
    visible,
    wait,
)

REQUESTER = "data_user"
OFFICES = "vc_issuer"
OWNER = "data_owner"

RECORDS_OFFICE = "University records office"
ETHICS_REGISTRY = "Ethics registry"
IRB_OFFICE = "Best University IRB office"
SESSION_KEYS = "Session keys"

PI = "did:example:pi_alice"
PROJECT = "did:example:glucose_study"
COMMITTEE = "did:example:committee_7"
UNIVERSITY = "did:example:best_university"

ASSET = "study_data"
DATA_PATH = os.environ.get("TUTORIAL_DATA_PATH", "/tmp/asset_data.txt")
GUARDIAN_PORT = "7900"

IRB_CARD = "ETHICS-APPROVAL-REQUIRED"
RECORDS = ["TeamCredential", "ProjectOwnershipCredential", "AffiliationCredential"]
ETHICS = ["IRBApprovalCredential", "EthicsCommitteeAccreditationCredential", "IntendedDataUseCredential"]


def requester_wallet(runner):
    """The DID of the wallet created for the requester when she first signed in."""
    open_page(runner, "/wallets/")
    did = runner.driver.execute_script(
        "var el = document.querySelector('.card .did-display'); return el ? el.textContent.trim() : '';"
    )
    if not did:
        raise StepFailed("the requester has no wallet")
    name = runner.driver.execute_script("return document.querySelector('.card h3').textContent.trim();")
    return did, name


def held_types(driver):
    """The credential types the open wallet page lists."""
    return driver.execute_script(
        "return Array.from(document.querySelectorAll('.credentials-table tr[data-fact]'))"
        ".map(function (tr) { return tr.dataset.fact; });"
    )


def use_checklist(runner, wallet_name):
    """Open the Use modal on the asset, choose the wallet, and read the checklist."""
    open_page(runner, "/")
    click(runner.driver, f"[data-action=open-use][data-asset-name='{ASSET}']")
    select = Select(visible(runner.driver, "#use-wallet-User"))
    select.select_by_visible_text(wallet_name)
    wait(runner.driver, SHORT_WAIT * 2).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "#use-checklist tr[data-fact]")
    )
    return read_checklist(runner.driver, "#use-checklist")


def run_workflow(runner):
    state = {}

    runner.step(f"Become {REQUESTER} (the requester)", lambda: as_identity(runner, REQUESTER))

    def read_wallet():
        state["wallet_did"], state["wallet_name"] = requester_wallet(runner)
        print(f"      wallet: {state['wallet_name']} {state['wallet_did']}", flush=True)

    runner.step("Read the requester's wallet DID", read_wallet)

    # ------------------------------------------------ the offices
    runner.step(f"Become {OFFICES} (the offices)", lambda: as_identity(runner, OFFICES))
    runner.step(
        "Create the records office",
        lambda: create_hand_signing_authority(
            runner, RECORDS_OFFICE, facts=RECORDS,
            checks="Keeps the university's teams, projects and appointments.",
        ),
    )
    runner.step(
        "Create the ethics registry",
        lambda: create_hand_signing_authority(
            runner, ETHICS_REGISTRY, facts=ETHICS,
            checks="Records committee approvals, accreditations and the uses projects declare.",
        ),
    )
    runner.step(
        "Create the IRB office",
        lambda: create_hand_signing_authority(
            runner, IRB_OFFICE, facts=["IRBClearanceCredential"], checks="Reviews each protocol before clearing it."
        ),
    )
    runner.step("Create the session-key authority", lambda: create_system_authority(runner, SESSION_KEYS))

    # ------------------------------------------------ the owner
    runner.step(f"Become {OWNER} (the dataset owner)", lambda: as_identity(runner, OWNER))
    runner.step(
        f"Publish {ASSET} behind a download guardian",
        lambda: register_asset(
            runner, name=ASSET, path=DATA_PATH, guardian_title="Download", port=GUARDIAN_PORT
        ),
    )

    def expose_the_card():
        review = expose(
            runner,
            asset=ASSET,
            cards=[IRB_CARD],
            parameters={},
            authorities={
                **{t: [RECORDS_OFFICE] for t in RECORDS},
                **{t: [ETHICS_REGISTRY] for t in ETHICS},
                "IRBClearanceCredential": [IRB_OFFICE],
                "publicKeyCredential": [SESSION_KEYS],
            },
        )
        if not review.startswith("Requesters will present one of: IRB clearance + Intended data use + Session key;"):
            raise StepFailed(f"the review line does not offer the clearance first: {review}")

    runner.step("Expose it under the ethics approval card", expose_the_card)

    # ------------------------------------------------ the requester, before
    runner.step(f"Become {REQUESTER} again", lambda: as_identity(runner, REQUESTER))

    def ask_for_the_shortest_way():
        found = use_checklist(runner, state["wallet_name"])
        expect_statuses(found, {
            "IRBClearanceCredential": "ask", "IntendedDataUseCredential": "ask", "publicKeyCredential": "automatic",
        }, ASSET)
        row = runner.driver.find_element(By.CSS_SELECTOR, "#use-checklist tr[data-fact=IRBClearanceCredential]")
        if f"Ask {IRB_OFFICE}." not in row.text:
            raise StepFailed(f"the checklist should say whom to ask: {row.text!r}")
        if runner.driver.find_element(By.CSS_SELECTOR, "#use-submit").is_enabled():
            raise StepFailed("Use is enabled although credentials are missing")
        click(runner.driver, "[data-modal-close=use-modal]")

    runner.step("Her checklist says to ask the IRB office and the ethics registry", ask_for_the_shortest_way)

    # ------------------------------------------------ the chain
    runner.step(f"Become {OFFICES} again", lambda: as_identity(runner, OFFICES))

    def deliver_chain():
        wallet = state["wallet_did"]
        open_authority(runner, RECORDS_OFFICE)
        sign_as_authority(runner, fact="TeamCredential", about=wallet, holder=wallet,
                          claims={"MemberOfTeamOf": PI})
        sign_as_authority(runner, fact="ProjectOwnershipCredential", about=PI, holder=wallet,
                          claims={"Owns": PROJECT})
        sign_as_authority(runner, fact="AffiliationCredential", about=wallet, holder=wallet,
                          claims={"isMemberOf": UNIVERSITY, "typeOfMembership": "staff"})
        open_authority(runner, ETHICS_REGISTRY)
        sign_as_authority(runner, fact="IRBApprovalCredential", about=PROJECT, holder=wallet,
                          claims={"isApprovedByEthicsCommittee": COMMITTEE, "purposes": ["HMB"]})
        sign_as_authority(runner, fact="EthicsCommitteeAccreditationCredential", about=COMMITTEE, holder=wallet,
                          claims={"ResponsibleFor": UNIVERSITY})
        sign_as_authority(runner, fact="IntendedDataUseCredential", about=PROJECT, holder=wallet,
                          claims={"useOnlyFor": {"purposes": ["HMB"], "diseases": ["MONDO:0005015"]}})

    runner.step("The offices deliver the chain to her wallet", deliver_chain)

    # ------------------------------------------------ the requester, after
    runner.step(f"Become {REQUESTER} once more", lambda: as_identity(runner, REQUESTER))

    def chain_held():
        open_wallet(runner, state["wallet_name"])
        held = held_types(runner.driver)
        if not set(RECORDS + ETHICS) <= set(held):
            raise StepFailed(f"the wallet holds {sorted(held)}, not the whole chain")

    runner.step("Her wallet lists the chain", chain_held)

    def download():
        found = use_checklist(runner, state["wallet_name"])
        expect_statuses(found, {**{t: "held" for t in RECORDS + ETHICS}, "publicKeyCredential": "automatic"}, ASSET)
        wait(runner.driver, SHORT_WAIT).until(
            lambda d: d.find_element(By.CSS_SELECTOR, "#use-submit").is_enabled()
        )
        click(runner.driver, "#use-submit")
        run_flow(runner.driver)
        output = visible(runner.driver, "#use-result-output", SHORT_WAIT * 2).text
        if "The eagle lands at midnight." not in output:
            raise StepFailed(f"unexpected data: {output!r}")
        print(f"      data: {output.strip()}", flush=True)

    runner.step("The graph joins the chain, and the data comes back", download)

    def no_clearance_needed():
        open_wallet(runner, state["wallet_name"])
        if "IRBClearanceCredential" in held_types(runner.driver):
            raise StepFailed("her wallet holds an IRB clearance, which the graph should not have needed")

    runner.step("She never needed a clearance from the IRB office", no_clearance_needed)


if __name__ == "__main__":
    sys.exit(webui.main(run_workflow, (DATA_PATH,), __doc__))
