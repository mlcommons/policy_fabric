package pf.components.irb_clearance

import rego.v1

# IRBClearance: the requester belongs to the institution whose accredited IRB
# approved the requester's project.
#   approval    InstitutionalIRBApprovalCredential  about the project, {institution, purposes}
#   affiliation AffiliationCredential               about the requester, isMemberOf
#   membership  ProjectMembershipCredential         about the requester, {project}
# -> IRBClearanceCredential about the requester, {project, purposes}.
interface := {
	"output": "IRBClearanceCredential",
	"inputs": {
		"approval": {"type": "InstitutionalIRBApprovalCredential", "role": "User"},
		"affiliation": {"type": "AffiliationCredential", "role": "User"},
		"membership": {"type": "ProjectMembershipCredential", "role": "User"},
	},
	"policy_data_schema": {},
}

output := [cred |
	some approval in input.inputs.approval
	some affiliation in input.inputs.affiliation
	some membership in input.inputs.membership
	affiliation.subject == membership.subject
	affiliation.claims.isMemberOf == approval.claims.institution
	approval.subject == membership.claims.project
	cred := {
		"type": "IRBClearanceCredential",
		"subject": membership.subject,
		"claims": {
			"project": membership.claims.project,
			"purposes": approval.claims.purposes,
		},
		"evidence": evidence([approval, affiliation, membership]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
