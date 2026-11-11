package pf.components.institutional_irb_approval

import rego.v1

# InstitutionalIRBApproval: the project was approved by an ethics committee that
# is accredited as responsible for an institution.
#   accreditation EthicsCommitteeAccreditationCredential  about the committee, ResponsibleFor = the institution
#   irb           IRBApprovalCredential                   about the project, isApprovedByEthicsCommittee, purposes
# -> InstitutionalIRBApprovalCredential about the project, {institution, purposes}.
# purposes is a new claim of IRBApprovalCredential: the purposes the IRB approved.
interface := {
	"output": "InstitutionalIRBApprovalCredential",
	"inputs": {
		"accreditation": {"type": "EthicsCommitteeAccreditationCredential", "role": "User"},
		"irb": {"type": "IRBApprovalCredential", "role": "User"},
	},
	"policy_data_schema": {},
}

output := [cred |
	some accreditation in input.inputs.accreditation
	some irb in input.inputs.irb
	accreditation.subject == irb.claims.isApprovedByEthicsCommittee
	cred := {
		"type": "InstitutionalIRBApprovalCredential",
		"subject": irb.subject,
		"claims": {
			"institution": accreditation.claims.ResponsibleFor,
			"purposes": irb.claims.purposes,
		},
		"evidence": evidence([accreditation, irb]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
