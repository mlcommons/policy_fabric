package pf.components.user_specific_restriction

import rego.v1

# UserSpecificRestriction, the card component of User Specific Restriction (DUO_0000026):
# the requester's platform account belongs to an approved user, is of an allowed account
# type, or has a profile status the owner accepts.
#   userPlatform  UserPlatformCredential  about the requester, userId, accountType, profileStatus
# -> Decision about the requester.
interface := {
	"output": "Decision",
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

# for whom the condition holds
subjects contains account.subject if {
	some account in input.inputs.userPlatform
	user_qualifies(account)
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

user_qualifies(account) if account.claims.userId in input.policy_data.approvedUsers

user_qualifies(account) if account.claims.accountType in input.policy_data.allowedAccountTypes

user_qualifies(account) if account.claims.profileStatus in input.policy_data.requiredProfileStatuses
