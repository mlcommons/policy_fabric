package pf.components.institution_specific_restriction_for_inference_test

import rego.v1

import data.pf.components.institution_specific_restriction_for_inference

affiliation := {"type": "AffiliationCredential", "issuer": "did:example:university", "subject": "did:pdo:user-wallet",
	"claims": {"isMemberOf": "did:example:university", "typeOfMembership": "student"}, "evidence": [0]}

wallet_key := {"type": "WalletVerifyingKeyCredential", "issuer": "did:example:wallet-key-authority",
	"subject": "did:pdo:user-wallet", "claims": {"verifying_key": "WALLETPEM"}, "evidence": [1]}

ownership := {"type": "ScriptOwnershipCredential", "issuer": "did:pdo:user-wallet", "subject": "did:pdo:script",
	"claims": {"ownedBy": "did:pdo:user-wallet"}, "evidence": [2]}

condition(affiliations, keys, ownerships) := out if {
	out := institution_specific_restriction_for_inference.output with input as {
		"inputs": {"affiliation": affiliations, "walletVerifyingKey": keys, "scriptOwnership": ownerships},
		"policy_data": {"allowedInstitutions": ["did:example:university"]}, "request": {},
	}
}

test_a_member_of_an_allowed_institution_owns_the_script if {
	condition([affiliation], [wallet_key], [ownership]) == [{
		"type": "DataUseConditionCredential", "subject": "did:pdo:script",
		"claims": {}, "evidence": [0, 1, 2],
		"key_checks": [{"index": 2, "key": "WALLETPEM", "key_type": "ec"}],
	}]
}

test_an_institution_the_owner_does_not_allow if {
	condition([object.union(affiliation, {"claims": {"isMemberOf": "did:example:elsewhere"}})], [wallet_key], [ownership]) == []
}

test_the_wallet_key_of_someone_else if {
	condition([affiliation], [object.union(wallet_key, {"subject": "did:pdo:other-wallet"})], [ownership]) == []
}

test_an_ownership_signed_by_someone_else if {
	condition([affiliation], [wallet_key], [object.union(ownership, {"issuer": "did:pdo:other-wallet"})]) == []
}

test_an_ownership_naming_someone_else if {
	condition([affiliation], [wallet_key], [object.union(ownership, {"claims": {"ownedBy": "did:pdo:other-wallet"}})]) == []
}
