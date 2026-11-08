# Accredited-committee check
# Issues an EthicsApprovalCredential to a project member when the project is
# approved by an ethics committee accredited for the institution of the PI who
# owns it. The approval is for the project the request names.

package subpolicy

import rego.v1

requirements := {"User": [
	"TeamCredential",
	"ProjectOwnershipCredential",
	"AffiliationCredential",
	"IRBApprovalCredential",
	"EthicsCommitteeAccreditationCredential",
]}

issues := "EthicsApprovalCredential"

teams := [c | some c in input.presentations.User; c.type == "TeamCredential"; c.trusted]

ownerships := [c | some c in input.presentations.User; c.type == "ProjectOwnershipCredential"; c.trusted]

affiliations := [c | some c in input.presentations.User; c.type == "AffiliationCredential"; c.trusted]

approvals := [c | some c in input.presentations.User; c.type == "IRBApprovalCredential"; c.trusted]

accreditations := [c |
	some c in input.presentations.User
	c.type == "EthicsCommitteeAccreditationCredential"
	c.trusted
]

# member -> PI -> project -> committee, with the committee responsible for the
# PI's institution
chains := [chain |
	some team in teams
	team.subject == input.holders.User
	some ownership in ownerships
	ownership.subject == team.claims.MemberOfTeamOf
	ownership.claims.Owns == input.request.project
	some affiliation in affiliations
	affiliation.subject == ownership.subject
	some approval in approvals
	approval.subject == input.request.project
	some accreditation in accreditations
	accreditation.subject == approval.claims.isApprovedByEthicsCommittee
	accreditation.claims.ResponsibleFor == affiliation.claims.isMemberOf
	chain := {
		"committee": accreditation.subject,
		"links": [team, ownership, affiliation, approval, accreditation],
	}
]

default decision := false

decision if count(chains) > 0

verification_tasks := [{"index": c.index} | some c in chains[0].links]

credential := {
	"subject": input.holders.User,
	"claims": {"project": input.request.project, "approvedBy": chains[0].committee},
}

result := {
	"decision": true,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"credential": credential,
} if decision

result := {"decision": false, "verification_tasks": [], "vc_supplied_verification_tasks": []} if not decision
