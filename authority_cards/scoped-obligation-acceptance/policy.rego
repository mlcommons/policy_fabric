# Scoped obligation acceptance
# Issues an ObligationAcceptanceCredential to a project member, for the project
# the request names, listing every obligation the PI's institution accepted for
# it, each scoped to a dataset: member -> PI -> project and institution -> scoped
# agreement.

package subpolicy

import rego.v1

requirements := {"User": [
	"TeamCredential",
	"ProjectOwnershipCredential",
	"AffiliationCredential",
	"ScopedAgreementCredential",
	"AgreementCredential",
]}

issues := "ObligationAcceptanceCredential"

teams := [c | some c in input.presentations.User; c.type == "TeamCredential"; c.trusted]

ownerships := [c | some c in input.presentations.User; c.type == "ProjectOwnershipCredential"; c.trusted]

affiliations := [c | some c in input.presentations.User; c.type == "AffiliationCredential"; c.trusted]

scoped_agreements := [c | some c in input.presentations.User; c.type == "ScopedAgreementCredential"; c.trusted]

agreements := [c | some c in input.presentations.User; c.type == "AgreementCredential"; c.trusted]

chains := [chain |
	some team in teams
	team.subject == input.holders.User
	some ownership in ownerships
	ownership.subject == team.claims.MemberOfTeamOf
	ownership.claims.Owns == input.request.project
	some affiliation in affiliations
	affiliation.subject == ownership.subject
	some scoped in scoped_agreements
	scope := scoped.claims.agreementInfo.scope
	scope.project == input.request.project
	some agreement in agreements
	agreement.subject == affiliation.claims.isMemberOf
	agreement.claims.agreementInfo.documentID == scoped.subject
	chain := {
		"scope": {"obligation": scope.obligation, "dataset": scope.dataset, "agreement": scoped.subject},
		"links": [team, ownership, affiliation, scoped, agreement],
	}
]

default decision := false

decision if count(chains) > 0

scopes := [scope | some scope in {chain.scope | some chain in chains}]

links := {link | some chain in chains; some link in chain.links}

verification_tasks := [{"index": c.index} | some c in links]

credential := {"subject": input.holders.User, "claims": {"project": input.request.project, "scopes": scopes}}

result := {
	"decision": true,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": [],
	"credential": credential,
} if decision

result := {"decision": false, "verification_tasks": [], "vc_supplied_verification_tasks": []} if not decision
