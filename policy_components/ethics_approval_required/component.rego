package pf.components.ethics_approval_required

import rego.v1

# EthicsApprovalRequired, the card component of Ethics Approval Required (DUO_0000021):
# the requester is cleared by an IRB for a project, and that project intends to
# use the data only for purposes the IRB approved.
#   clearance IRBClearanceCredential     about the requester, {project, purposes}
#   use       IntendedDataUseCredential  about the project, useOnlyFor.purposes
# -> DataUseConditionCredential about the requester. No policy data.
interface := {
	"output": "DataUseConditionCredential",
	"inputs": {
		"clearance": {"type": "IRBClearanceCredential", "role": "User"},
		"use": {"type": "IntendedDataUseCredential", "role": "User"},
	},
	"policy_data_schema": {},
}

output := [cred |
	some clearance in input.inputs.clearance
	some use in input.inputs.use
	use.subject == clearance.claims.project
	approved_use(use.claims.useOnlyFor.purposes, clearance.claims.purposes)
	cred := {
		"type": "DataUseConditionCredential",
		"subject": clearance.subject,
		"claims": {},
		"evidence": evidence([clearance, use]),
	}
]

# Every intended purpose is one the IRB approved. A use that names no purpose
# does not pass: "every" alone would let an empty list through.
approved_use(intended, approved) if {
	count(intended) > 0
	every purpose in intended {
		purpose in approved
	}
}

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
