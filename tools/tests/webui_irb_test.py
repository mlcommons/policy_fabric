"""The ethics approval tutorial, driven through the web UI.

Every click `docs/docs/tutorial_irb.md` asks a reader to make, made by a browser
instead, in the same order:

* the offices create a records office and an ethics registry (hand-signing), the
  accredited-committee check (rule-based, accepting both offices for its inputs),
  the IRB office (hand-signing) and session keys (system);
* the owner exposes a dataset under the ethics approval card, accepting both the
  IRB office and the committee check for the one fact it reads;
* the requester's checklist says to ask the IRB office, since she holds nothing
  the committee check could read;
* the offices deliver the chain -- credentials about her PI, project and the
  approving committee -- to her wallet;
* her checklist now says the approval is obtained on the way, and the download
  returns the data: the committee check issued her an ethics approval, and the
  policy accepted it.

What the run proves: one policy, one fact, two authorities that establish it in
completely different ways, and a checklist that says which way the requester can
qualify before anything is submitted.

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
    accept_authority,
    as_identity,
    click,
    create_hand_signing_authority,
    create_rule_based_authority,
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
COMMITTEE_CHECK = "Accredited-committee check"
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
COMMITTEE_CARD = "ACCREDITED-COMMITTEE-CHECK"


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


def held_facts(driver):
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
            runner, RECORDS_OFFICE,
            facts=["TeamCredential", "ProjectOwnershipCredential", "AffiliationCredential"],
            checks="Keeps the university's teams, projects and appointments.",
        ),
    )
    runner.step(
        "Create the ethics registry",
        lambda: create_hand_signing_authority(
            runner, ETHICS_REGISTRY,
            facts=["IRBApprovalCredential", "EthicsCommitteeAccreditationCredential"],
            checks="Records committee approvals and accreditations.",
        ),
    )
    runner.step(
        "Create the accredited-committee check from its authority card",
        lambda: create_rule_based_authority(runner, COMMITTEE_CHECK, card=COMMITTEE_CARD),
    )

    def accept_inputs():
        open_authority(runner, COMMITTEE_CHECK)
        visible(runner.driver, "#authority-rule")
        for fact in ("TeamCredential", "ProjectOwnershipCredential", "AffiliationCredential"):
            accept_authority(runner, fact, RECORDS_OFFICE)
        for fact in ("IRBApprovalCredential", "EthicsCommitteeAccreditationCredential"):
            accept_authority(runner, fact, ETHICS_REGISTRY)

    runner.step("The committee check accepts the two offices for its inputs", accept_inputs)
    runner.step(
        "Create the IRB office",
        lambda: create_hand_signing_authority(
            runner, IRB_OFFICE, facts=["EthicsApprovalCredential"], checks="Reviews each protocol before approving it."
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

    def expose_with_both():
        review = expose(
            runner,
            asset=ASSET,
            cards=[IRB_CARD],
            parameters={},
            authorities={
                "EthicsApprovalCredential": [IRB_OFFICE, COMMITTEE_CHECK],
                "publicKeyCredential": [SESSION_KEYS],
            },
        )
        if f"Ethics approval ({IRB_OFFICE} or {COMMITTEE_CHECK})" not in review:
            raise StepFailed(f"the review line does not name both authorities: {review}")

    runner.step("Expose it under the ethics approval card, accepting both authorities", expose_with_both)

    # ------------------------------------------------ the requester, before
    runner.step(f"Become {REQUESTER} again", lambda: as_identity(runner, REQUESTER))

    def nothing_to_read_yet():
        found = use_checklist(runner, state["wallet_name"])
        expect_statuses(
            found, {"EthicsApprovalCredential": "ask", "publicKeyCredential": "automatic"}, ASSET
        )
        row = runner.driver.find_element(By.CSS_SELECTOR, "#use-checklist tr[data-fact=EthicsApprovalCredential]")
        if f"Ask {IRB_OFFICE}." not in row.text:
            raise StepFailed(f"the checklist should say whom to ask: {row.text!r}")
        if runner.driver.find_element(By.CSS_SELECTOR, "#use-submit").is_enabled():
            raise StepFailed("Use is enabled although a fact is missing")
        # the approval is about a project, and none of her wallets names one yet
        visible(runner.driver, "#use-project-none")
        click(runner.driver, "[data-modal-close=use-modal]")

    runner.step("Her checklist says to ask the IRB office", nothing_to_read_yet)

    # ------------------------------------------------ the chain
    runner.step(f"Become {OFFICES} again", lambda: as_identity(runner, OFFICES))

    def deliver_chain():
        wallet = state["wallet_did"]
        open_authority(runner, RECORDS_OFFICE)
        sign_as_authority(runner, fact="TeamCredential", about=wallet, holder=wallet,
                          claims={"MemberOfTeamOf": PI})
        sign_as_authority(runner, fact="ProjectOwnershipCredential", about=PI, holder=wallet,
                          claims={"Owns": PROJECT})
        sign_as_authority(runner, fact="AffiliationCredential", about=PI, holder=wallet,
                          claims={"isMemberOf": UNIVERSITY, "typeOfMembership": "faculty"})
        open_authority(runner, ETHICS_REGISTRY)
        sign_as_authority(runner, fact="IRBApprovalCredential", about=PROJECT, holder=wallet,
                          claims={"isApprovedByEthicsCommittee": COMMITTEE})
        sign_as_authority(runner, fact="EthicsCommitteeAccreditationCredential", about=COMMITTEE, holder=wallet,
                          claims={"ResponsibleFor": UNIVERSITY})

    runner.step("The offices deliver the chain to her wallet", deliver_chain)

    # ------------------------------------------------ the requester, after
    runner.step(f"Become {REQUESTER} once more", lambda: as_identity(runner, REQUESTER))

    def chain_held():
        open_wallet(runner, state["wallet_name"])
        held = held_facts(runner.driver)
        expected = {"TeamCredential", "ProjectOwnershipCredential", "AffiliationCredential",
                    "IRBApprovalCredential", "EthicsCommitteeAccreditationCredential"}
        if not expected <= set(held):
            raise StepFailed(f"the wallet holds {sorted(held)}, not the whole chain")

    runner.step("Her wallet lists the chain", chain_held)

    def download():
        found = use_checklist(runner, state["wallet_name"])
        expect_statuses(
            found, {"EthicsApprovalCredential": "automatic", "publicKeyCredential": "automatic"}, ASSET
        )
        # the project her PI owns, as the copy of the ownership in her wallet names it
        Select(visible(runner.driver, "#use-project")).select_by_value(PROJECT)
        wait(runner.driver, SHORT_WAIT).until(
            lambda d: d.find_element(By.CSS_SELECTOR, "#use-submit").is_enabled()
        )
        click(runner.driver, "#use-submit")
        run_flow(runner.driver)
        output = visible(runner.driver, "#use-result-output", SHORT_WAIT * 2).text
        if "The eagle lands at midnight." not in output:
            raise StepFailed(f"unexpected data: {output!r}")
        print(f"      data: {output.strip()}", flush=True)

    runner.step("The committee check qualifies her, and the data comes back", download)

    def approval_from_the_rule():
        open_wallet(runner, state["wallet_name"])
        signer = runner.driver.execute_script(
            "var tr = document.querySelector('.credentials-table tr[data-fact=EthicsApprovalCredential]');"
            "return tr ? tr.children[2].textContent.trim() : '';"
        )
        if signer != COMMITTEE_CHECK:
            raise StepFailed(f"her ethics approval is signed by {signer!r}, not the committee check")
        print(f"      Ethics approval signed by {signer}", flush=True)

    runner.step("Her new ethics approval was issued by the committee check", approval_from_the_rule)


if __name__ == "__main__":
    sys.exit(webui.main(run_workflow, (DATA_PATH,), __doc__))
