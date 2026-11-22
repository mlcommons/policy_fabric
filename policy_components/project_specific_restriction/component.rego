package pf.components.project_specific_restriction

import rego.v1

# ProjectSpecificRestriction, the card component of Project Specific Restriction (DUO_0000027):
# the requester's project is one the owner approved and has an intended use, and the requester
# accepted the terms.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   intendedDataUse    IntendedDataUseCredential    about the project
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
		"properties": {"approvedProjects": {
			"type": "array",
			"items": {"type": "string"},
			"description": "Project DIDs the owner approved.",
		}},
		"required": ["approvedProjects"],
	},
}

# for whom the condition holds
subjects contains membership.subject if {
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	use.subject in input.policy_data.approvedProjects
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
}

output := {"allow": count(subjects) > 0, "parameters": {"subject": sort(subjects)}}
