package pf.components.collaboration_required

import rego.v1

# CollaborationRequired, the card component of Collaboration Required (DUO_0000020): the
# requester's institution agreed to terms with the Collaboration obligation, scoped to the
# owner's dataset and the requester's project.
#   projectMembership  ProjectMembershipCredential  about the requester, project
#   affiliation        AffiliationCredential        about the requester, isMemberOf
#   scopedAgreement    ScopedAgreementCredential    about the terms, agreementInfo.scope
#   agreement          AgreementCredential          about the institution, agreementInfo.documentID
# -> DataUseConditionCredential about the requester.
interface := {
	"output": "DataUseConditionCredential",
	"inputs": {
		"projectMembership": {"type": "ProjectMembershipCredential", "role": "User"},
		"affiliation": {"type": "AffiliationCredential", "role": "User"},
		"scopedAgreement": {"type": "ScopedAgreementCredential", "role": "User"},
		"agreement": {"type": "AgreementCredential", "role": "User"},
	},
	"policy_data_schema": {
		"type": "object",
		"properties": {"datasetID": {
			"type": "string",
			"description": "DID of the governed dataset.",
		}},
		"required": ["datasetID"],
	},
}

output := [condition |
	some membership in input.inputs.projectMembership
	some affiliation in input.inputs.affiliation
	affiliation.subject == membership.subject
	some scoped in input.inputs.scopedAgreement
	scoped.claims.agreementInfo.scope.obligation == "Collaboration"
	scoped.claims.agreementInfo.scope.dataset == input.policy_data.datasetID
	scoped.claims.agreementInfo.scope.project == membership.claims.project
	some agreement in input.inputs.agreement
	agreement.subject == affiliation.claims.isMemberOf
	agreement.claims.agreementInfo.documentID == scoped.subject
	condition := {
		"type": "DataUseConditionCredential",
		"subject": membership.subject,
		"claims": {},
		"evidence": evidence([membership, affiliation, scoped, agreement]),
	}
]

# The presented credentials an output rests on: the union of its inputs' evidence, sorted.
evidence(creds) := result if {
	ids := {i | some c in creds; some i in c.evidence}
	result := sort(ids)
}
