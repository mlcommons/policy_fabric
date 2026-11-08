import unittest

from app.credentials import Held, accepted, accepted_issuers, contract_id_of, held_credentials, trusted_types

from .fixtures import REQUESTER, trusting, vc


class Credentials(unittest.TestCase):
    def test_contract_id_of_a_did_drops_prefix_and_fragment(self):
        self.assertEqual(contract_id_of("did:pdo:abc/1=#poc"), "abc/1=")
        self.assertEqual(contract_id_of("abc/1="), "abc/1=")
        self.assertEqual(contract_id_of("did:example:x"), "did:example:x")

    def test_a_stored_credential_is_decoded(self):
        held = held_credentials({"d1": vc("LocationCredential", REQUESTER, {"locatedAt": {"country": "US"}})})[0]
        self.assertEqual((held.digest, held.type, held.signer), ("d1", "LocationCredential", "registry"))
        self.assertEqual(held.claims["locatedAt"]["country"], "US")
        self.assertTrue(held.is_about("did:pdo:requester"))
        self.assertEqual(held.signer_did, "did:pdo:registry")

    def test_accepted_from_a_trusted_signer_for_its_type(self):
        held = Held(vc("LocationCredential", REQUESTER), "d1")
        self.assertTrue(accepted(held, trusting("registry", ["LocationCredential"])))
        self.assertFalse(accepted(held, trusting("registry", ["AffiliationCredential"])))
        self.assertFalse(accepted(held, trusting("someone-else", ["LocationCredential"])))

    def test_the_trusted_context_must_be_a_prefix_of_the_signing_path(self):
        held = Held(vc("LocationCredential", REQUESTER, context_path=("poc", "sub")), "d1")
        self.assertTrue(accepted(held, trusting("registry", ["LocationCredential"], prefix_path=())))
        self.assertTrue(accepted(held, trusting("registry", ["LocationCredential"], prefix_path=("poc",))))
        self.assertFalse(accepted(held, trusting("registry", ["LocationCredential"], prefix_path=("other",))))

    def test_a_credential_whose_issuer_is_not_its_signer_is_not_accepted(self):
        held = Held(vc("LocationCredential", REQUESTER, issuer="did:pdo:impostor"), "d1")
        self.assertFalse(accepted(held, trusting("registry", ["LocationCredential"])))

    def test_accepted_issuers_for_a_type(self):
        trusted = {**trusting("a", ["LocationCredential"]), **trusting("b", ["AffiliationCredential"])}
        self.assertEqual(accepted_issuers(trusted, "LocationCredential"), ["a"])

    def test_trusted_types_from_any_context_and_from_one(self):
        trusted = {"a": [
            {"verifying_context": {"prefix_path": ["poc"]}, "credential_types": ["LocationCredential"]},
            {"verifying_context": {"prefix_path": ["other"]}, "credential_types": ["AffiliationCredential"]},
        ]}
        self.assertEqual(trusted_types(trusted, "a"), {"LocationCredential", "AffiliationCredential"})
        self.assertEqual(trusted_types(trusted, "b"), set())
        held = Held(vc("AffiliationCredential", REQUESTER, signer="a", context_path=("poc",)), "d1")
        self.assertFalse(accepted(held, trusted))
