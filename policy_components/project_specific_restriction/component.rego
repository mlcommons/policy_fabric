package pf.components.project_specific_restriction

import rego.v1

# ProjectSpecificRestriction, the card component of Project Specific Restriction (DUO_0000027):
# the requester's project is one the owner approved and has an intended use, and the requester
# accepted the terms.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   intendedDataUse    IntendedDataUseCredential    about the project
#   agreement          AgreementCredential          about the requester
# -> DataUseConditionCredential about the requester.
interface := {
	"output": "DataUseConditionCredential",
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

output := [condition |
	some membership in input.inputs.projectMembership
	some use in input.inputs.intendedDataUse
	use.subject == membership.claims.project
	use.subject in input.policy_data.approvedProjects
	some agreement in input.inputs.agreement
	agreement.subject == membership.subject
	condition := {
		"type": "DataUseConditionCredential",
		"subject": membership.subject,
		"claims": {},
		"evidence": evidence([membership, use, agreement]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
