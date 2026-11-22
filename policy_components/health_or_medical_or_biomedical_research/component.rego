package pf.components.health_or_medical_or_biomedical_research

import rego.v1

# HealthOrMedicalOrBiomedicalResearch, the card component of Health or Medical or Biomedical
# Research (DUO_0000006): the requester's project intends to use the data for a health,
# medical or biomedical purpose the owner allows and for no purpose the owner prohibits, and
# the requester accepted the terms.
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
		"properties": {
			"allowedPurposes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Health, medical or biomedical purpose terms the owner allows.",
			},
			"prohibitedPurposes": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Purpose terms the owner prohibits, such as population origins or ancestry research.",
			},
		},
		"required": ["allowedPurposes", "prohibitedPurposes"],
	},
}

# for whom the condition holds
subjects contains membership.subject if {
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	allowed_purpose(use)
	no_prohibited_purpose(use)
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}

allowed_purpose(use) if {
	some purpose in use.claims.useOnlyFor.purposes
	purpose in input.policy_data.allowedPurposes
}

# The list is bound outside the "not", so that policy data without it fails the check
# instead of prohibiting nothing.
no_prohibited_purpose(use) if {
	prohibited := input.policy_data.prohibitedPurposes
	every purpose in use.claims.useOnlyFor.purposes {
		not purpose in prohibited
	}
}
