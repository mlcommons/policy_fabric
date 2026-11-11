package pf.components.user_specific_restriction_test

import rego.v1

import data.pf.components.user_specific_restriction

account := {"type": "UserPlatformCredential", "issuer": "did:example:platform", "subject": "did:example:user",
	"claims": {"userId": "did:example:user", "accountType": "individual", "profileStatus": "pending", "isUser": true}, "evidence": [0]}

unapproved := object.union(account, {"claims": {"userId": "did:example:unknown"}})

grant(accounts) := out if {
	out := user_specific_restriction.output with input as {
		"inputs": {"userPlatform": accounts},
		"policy_data": {
			"approvedUsers": ["did:example:user"],
			"allowedAccountTypes": ["institutional"],
			"requiredProfileStatuses": ["verified"],
		},
		"request": {},
	}
}

test_an_approved_user if {
	grant([account]) == [{"type": "DownloadGrantCredential", "subject": "did:example:user", "claims": {}, "evidence": [0]}]
}

test_an_allowed_account_type if {
	count(grant([object.union(unapproved, {"claims": {"accountType": "institutional"}})])) == 1
}

test_a_profile_status_the_owner_accepts if {
	count(grant([object.union(unapproved, {"claims": {"profileStatus": "verified"}})])) == 1
}

test_one_grant_for_several_routes if {
	count(grant([object.union(account, {"claims": {"accountType": "institutional", "profileStatus": "verified"}})])) == 1
}

test_no_route if {
	grant([unapproved]) == []
}
