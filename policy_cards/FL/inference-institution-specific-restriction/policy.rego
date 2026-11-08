# FL-IS -- Institution-specific inference
# The requester is a member of an institution the owner allows, and owns the
# script they bring: their own wallet signed the ownership claim, and the
# signature is checked against the wallet's key as an authority attested it.

package subpolicy

import rego.v1

requirements := {
	"User": ["AffiliationCredential", "WalletVerifyingKeyCredential"],
	"Script": ["ScriptOwnershipCredential"],
}

affiliations := [c |
	some c in input.presentations.User
	c.type == "AffiliationCredential"
	c.trusted
	c.subject == input.holders.User
	c.claims.isMemberOf in input.policy_data.allowedInstitutions
]

wallet_keys := [c |
	some c in input.presentations.User
	c.type == "WalletVerifyingKeyCredential"
	c.trusted
	c.subject == input.holders.User
]

ownerships := [c |
	some c in input.presentations.Script
	c.type == "ScriptOwnershipCredential"
	c.subject == input.holders.Script
	c.signer == input.holders.User
	c.claims.ownedBy == input.holders.User
]

default decision := false

decision if {
	count(affiliations) > 0
	count(wallet_keys) > 0
	count(ownerships) > 0
}

relied_on := array.concat(affiliations, wallet_keys)

verification_tasks := [{"index": c.index} | some c in relied_on]

# The ownership claim has no registered issuer, so it is checked against the
# wallet key instead. PDO contract keys are ECDSA, hence "ec".
vc_supplied_verification_tasks := [{"index": c.index, "key": wallet_keys[0].claims.verifying_key, "key_type": "ec"} |
	some c in ownerships
]

result := {
	"decision": decision,
	"verification_tasks": verification_tasks,
	"vc_supplied_verification_tasks": vc_supplied_verification_tasks,
}
