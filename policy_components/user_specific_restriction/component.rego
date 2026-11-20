package pf.components.user_specific_restriction

import rego.v1

# UserSpecificRestriction, the card component of User Specific Restriction (DUO_0000026):
# the requester's platform account belongs to an approved user, is of an allowed account
# type, or has a profile status the owner accepts.
#   userPlatform  UserPlatformCredential  about the requester, userId, accountType, profileStatus
# -> DataUseConditionCredential about the requester.
interface := {
	"output": "DataUseConditionCredential",
	"inputs": {"userPlatform": {"type": "UserPlatformCredential", "role": "User"}},
	"policy_data_schema": {
		"type": "object",
		"properties": {
			"approvedUsers": {
				"type": "array",
				"items": {"type": "string"},
				"description": "User identifiers the owner approves.",
			},
			"allowedAccountTypes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Account types the owner allows.",
			},
			"requiredProfileStatuses": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Profile statuses the owner accepts.",
			},
		},
		"required": ["approvedUsers", "allowedAccountTypes", "requiredProfileStatuses"],
	},
}

output := [condition |
	some account in input.inputs.userPlatform
	user_qualifies(account)
	condition := {
		"type": "DataUseConditionCredential",
		"subject": account.subject,
		"claims": {},
		"evidence": evidence([account]),
	}
]

user_qualifies(account) if account.claims.userId in input.policy_data.approvedUsers

user_qualifies(account) if account.claims.accountType in input.policy_data.allowedAccountTypes

user_qualifies(account) if account.claims.profileStatus in input.policy_data.requiredProfileStatuses

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
