package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

affiliation(institution) := testlib.credential(
	"AffiliationCredential",
	testlib.requester,
	{"isMemberOf": institution, "typeOfMembership": "faculty"},
)

wallet_key := testlib.credential("WalletVerifyingKeyCredential", testlib.requester, {"verifying_key": "WALLETPEM"})

# Signed by the requester's own wallet, which no policy agent registers as an issuer.
ownership(owner) := {
	"type": "ScriptOwnershipCredential",
	"issuer": owner,
	"signer": owner,
	"trusted": false,
	"subject": testlib.script,
	"claims": {"ownedBy": owner},
	"index": 0,
}

data_ := {"allowedInstitutions": ["did:example:university"]}

requester_held := [affiliation("did:example:university"), wallet_key]

test_requirements if {
	subpolicy.requirements == {
		"User": ["AffiliationCredential", "WalletVerifyingKeyCredential"],
		"Script": ["ScriptOwnershipCredential"],
	}
}

test_allows_a_member_who_owns_the_script if {
	r := subpolicy.result with input as testlib.inference_input(requester_held, [ownership(testlib.requester)], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}, {"index": 1}]
	r.vc_supplied_verification_tasks == [{"index": 2, "key": "WALLETPEM", "key_type": "ec"}]
	not "credential" in object.keys(r)
}

test_denies_a_member_of_another_institution if {
	held := [affiliation("did:example:elsewhere"), wallet_key]
	not subpolicy.result.decision with input as testlib.inference_input(held, [ownership(testlib.requester)], data_, {})
}

test_denies_a_script_owned_by_someone_else if {
	claim := ownership("did:pdo:someone-else")
	not subpolicy.result.decision with input as testlib.inference_input(requester_held, [claim], data_, {})
}

test_denies_an_ownership_claim_signed_by_another_wallet if {
	claim := object.union(ownership(testlib.requester), {"signer": "did:pdo:someone-else"})
	not subpolicy.result.decision with input as testlib.inference_input(requester_held, [claim], data_, {})
}

test_denies_without_an_attested_wallet_key if {
	held := [affiliation("did:example:university"), testlib.untrusted(wallet_key)]
	not subpolicy.result.decision with input as testlib.inference_input(held, [ownership(testlib.requester)], data_, {})
}
