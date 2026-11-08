package subpolicy_test

import data.subpolicy
import data.testlib
import rego.v1

account(user_id, account_type, status) := testlib.credential("UserPlatformCredential", testlib.requester, {
	"userId": user_id,
	"accountType": account_type,
	"profileStatus": status,
	"isUser": true,
})

data_ := {
	"approvedUsers": ["alice"],
	"allowedAccountTypes": ["researcher"],
	"requiredProfileStatuses": ["verified"],
}

test_requirements if {
	subpolicy.requirements == {"User": ["UserPlatformCredential"]}
}

test_allows_an_approved_user if {
	r := subpolicy.result with input as testlib.requester_input([account("alice", "guest", "new")], data_, {})
	r.decision
	r.verification_tasks == [{"index": 0}]
}

test_allows_an_allowed_account_type if {
	subpolicy.result.decision with input as testlib.requester_input([account("bob", "researcher", "new")], data_, {})
}

test_allows_a_required_profile_status if {
	subpolicy.result.decision with input as testlib.requester_input([account("bob", "guest", "verified")], data_, {})
}

test_denies_an_account_on_no_route if {
	not subpolicy.result.decision with input as testlib.requester_input([account("bob", "guest", "new")], data_, {})
}

test_denies_an_account_of_someone_else if {
	c := testlib.about_someone_else(account("alice", "researcher", "verified"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}

test_ignores_an_untrusted_account if {
	c := testlib.untrusted(account("alice", "researcher", "verified"))
	not subpolicy.result.decision with input as testlib.requester_input([c], data_, {})
}
