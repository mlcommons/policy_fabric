import unittest

from app import checklist

from .fixtures import REQUESTER, authority, held, trusting, vc

IRB_OFFICE = authority("did:pdo:irb#poc", "IRB office", "hand-signing", ["EthicsApprovalCredential"])
COMMITTEE = authority(
    "did:pdo:committee", "Accredited-committee check", "rule-based", ["EthicsApprovalCredential"],
    inputs={"User": ["TeamCredential", "IRBApprovalCredential"]},
)
SESSION_KEYS = authority("did:pdo:eka", "Session keys", "system", ["publicKeyCredential"])
DIRECTORY = [IRB_OFFICE, COMMITTEE, SESSION_KEYS]

NEEDS = {"User": ["EthicsApprovalCredential", "publicKeyCredential"]}


def wallet(*vcs):
    return {"User": (REQUESTER, held(*vcs))}


class Checklist(unittest.TestCase):
    def statuses(self, trusted, wallets, usable=lambda h: True):
        rows = checklist.checklist(NEEDS, trusted, wallets, DIRECTORY, usable, set())
        return {r["type"]: r for r in rows}

    def test_held_and_accepted(self):
        trusted = {**trusting("irb", ["EthicsApprovalCredential"]), **trusting("eka", ["publicKeyCredential"])}
        rows = self.statuses(trusted, wallet(
            vc("EthicsApprovalCredential", REQUESTER, signer="irb"),
            vc("publicKeyCredential", REQUESTER, signer="eka"),
        ))
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.HELD)
        self.assertTrue(checklist.ready(rows.values()))

    def test_a_system_authority_makes_a_fact_automatic(self):
        trusted = {**trusting("irb", ["EthicsApprovalCredential"]), **trusting("eka", ["publicKeyCredential"], ())}
        rows = self.statuses(trusted, wallet(vc("EthicsApprovalCredential", REQUESTER, signer="irb")))
        self.assertEqual(rows["publicKeyCredential"]["status"], checklist.AUTOMATIC)
        self.assertEqual(rows["publicKeyCredential"]["via"]["name"], "Session keys")

    def test_a_held_key_without_its_private_half_is_obtained_again(self):
        trusted = {**trusting("irb", ["EthicsApprovalCredential"]), **trusting("eka", ["publicKeyCredential"])}
        rows = self.statuses(
            trusted,
            wallet(vc("EthicsApprovalCredential", REQUESTER, signer="irb"), vc("publicKeyCredential", REQUESTER, signer="eka")),
            usable=lambda h: h.type != "publicKeyCredential",
        )
        self.assertEqual(rows["publicKeyCredential"]["status"], checklist.AUTOMATIC)

    def test_a_rule_based_authority_is_automatic_once_its_inputs_are_held(self):
        trusted = trusting("committee", ["EthicsApprovalCredential"], ())
        missing = self.statuses(trusted, wallet(vc("TeamCredential", REQUESTER)))
        self.assertEqual(missing["EthicsApprovalCredential"]["status"], checklist.UNREACHABLE)

        held_inputs = wallet(vc("TeamCredential", REQUESTER), vc("IRBApprovalCredential", "did:example:p1"))
        rows = self.statuses(trusted, held_inputs)
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.AUTOMATIC)

    def test_only_hand_signing_authorities_means_ask_them(self):
        rows = self.statuses(trusting("irb", ["EthicsApprovalCredential"]), wallet())
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.ASK)
        self.assertEqual(rows["EthicsApprovalCredential"]["authorities"], ["IRB office"])

    def test_ask_names_only_the_authorities_a_person_can_ask(self):
        trusted = {**trusting("irb", ["EthicsApprovalCredential"]),
                   **trusting("committee", ["EthicsApprovalCredential"], ())}
        rows = self.statuses(trusted, wallet(vc("TeamCredential", REQUESTER)))
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.ASK)
        self.assertEqual(rows["EthicsApprovalCredential"]["authorities"], ["IRB office"])

    def test_held_from_an_authority_the_asset_does_not_trust(self):
        rows = self.statuses(
            trusting("irb", ["EthicsApprovalCredential"]),
            wallet(vc("EthicsApprovalCredential", REQUESTER, signer="elsewhere")),
        )
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.HELD_NOT_ACCEPTED)
        self.assertFalse(checklist.ready(rows.values()))

    def test_no_accepted_authority_is_unreachable(self):
        rows = self.statuses({}, wallet())
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.UNREACHABLE)

    def test_an_accepted_authority_missing_from_the_directory_is_asked_by_id(self):
        rows = self.statuses(trusting("unlisted", ["EthicsApprovalCredential"]), wallet())
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.ASK)
        self.assertEqual(rows["EthicsApprovalCredential"]["authorities"], ["unlisted"])

    def test_a_fact_about_someone_else_is_not_held(self):
        rows = self.statuses(
            trusting("irb", ["EthicsApprovalCredential"]),
            wallet(vc("EthicsApprovalCredential", "did:pdo:someone-else", signer="irb")),
        )
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.ASK)

    def test_a_role_with_no_identity_chosen(self):
        rows = self.statuses(trusting("irb", ["EthicsApprovalCredential"]), {"User": None})
        self.assertEqual(rows["EthicsApprovalCredential"]["status"], checklist.ASK)


class SelfAsserted(unittest.TestCase):
    NEEDS = {"User": ["WalletVerifyingKeyCredential"], "Script": ["ScriptOwnershipCredential"]}
    SCRIPT = "did:pdo:script"

    def rows(self, script_vcs):
        wallets = {"User": (REQUESTER, []), "Script": (self.SCRIPT, held(*script_vcs))}
        rows = checklist.checklist(
            self.NEEDS, {}, wallets, DIRECTORY, lambda h: True, {"ScriptOwnershipCredential"}
        )
        return {r["type"]: r for r in rows}

    def ownership(self, signer):
        return vc("ScriptOwnershipCredential", self.SCRIPT, {"ownedBy": f"did:pdo:{signer}"},
                  signer=signer, context_path=(), issuer=f"did:pdo:{signer}")

    def test_signed_by_the_requesters_own_wallet_is_held(self):
        row = self.rows([self.ownership("requester")])["ScriptOwnershipCredential"]
        self.assertEqual((row["status"], row["self_asserted"]), (checklist.HELD, True))

    def test_unsigned_asks_the_requester_to_sign_it(self):
        self.assertEqual(self.rows([])["ScriptOwnershipCredential"]["status"], checklist.ASK)

    def test_signed_by_someone_else_is_not_held(self):
        row = self.rows([self.ownership("someone-else")])["ScriptOwnershipCredential"]
        self.assertEqual(row["status"], checklist.ASK)
