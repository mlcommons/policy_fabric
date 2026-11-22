package pf.components.genetic_studies_only

import rego.v1

# GeneticStudiesOnly, the card component of Genetic Studies Only (DUO_0000016): the
# requester's project intends to use the data for a genetic study purpose the owner allows,
# and the requester accepted the terms.
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
		"properties": {"allowedPurposes": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Genetic study purpose terms the owner allows.",
		}},
		"required": ["allowedPurposes"],
	},
}

# for whom the condition holds
subjects contains membership.subject if {
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	allowed_purpose(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

allowed_purpose(use) if {
	some purpose in use.claims.useOnlyFor.purposes
	purpose in input.policy_data.allowedPurposes
}
