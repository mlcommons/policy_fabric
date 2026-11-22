package pf.components.no_general_methods_research

import rego.v1

# NoGeneralMethodsResearch, the card component of No General Methods Research (DUO_0000015):
# the requester's project intends to use the data for no purpose the owner prohibits, such as
# methods development, and the requester accepted the terms.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   intendedDataUse    IntendedDataUseCredential    about the project, useOnlyFor.purposes
#   agreement          AgreementCredential          about the requester
# -> Decision about the requester.
interface := {
	"output": "Decision",
	"inputs": {
		"projectMembership": {"type": "ProjectMembershipCredential", "role": "User"},
		"intendedDataUse": {"type": "IntendedDataUseCredential", "role": "User"},
		"agreement": {"type": "AgreementCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"prohibitedPurposes": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Purpose terms the owner prohibits, such as methods development.",
		}},
		"required": ["prohibitedPurposes"],
	},
}

# for whom the condition holds
subjects contains membership.subject if {
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	no_prohibited_purpose(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

# The list is bound outside the "not", so that policy data without it fails the check
# instead of prohibiting nothing.
no_prohibited_purpose(use) if {
	prohibited := input.policy_data.prohibitedPurposes
	every purpose in use.claims.useOnlyFor.purposes {
		not purpose in prohibited
	}
}
