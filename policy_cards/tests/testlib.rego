# Builders for the input the policy agent hands a module, shared by every card's
# tests. Load it next to the folder under test:  opa test <folder> tests/testlib.rego

package testlib

import rego.v1

requester := "did:pdo:requester"

script := "did:pdo:script"

registry := "did:pdo:registry"

# A credential about subject, signed by the registry, which the policy agent
# trusts for every type.
credential(type, subject, claims) := {
	"type": type,
	"issuer": registry,
	"signer": registry,
	"trusted": true,
	"subject": subject,
	"claims": claims,
	"index": 0,
}

# The same credential from a signer the policy agent does not trust.
untrusted(c) := object.union(c, {"issuer": "did:pdo:stranger", "signer": "did:pdo:stranger", "trusted": false})

# The same credential about someone other than the holder.
about_someone_else(c) := object.union(c, {"subject": "did:pdo:someone-else"})

# Index credentials the way the contract does: globally, in presentation order.
numbered(credentials, offset) := [object.union(c, {"index": offset + i}) | some i, c in credentials]

# What a module sees when the requester presents credentials.
requester_input(credentials, policy_data, request) := {
	"presentations": {"User": numbered(credentials, 0)},
	"holders": {"User": requester},
	"request": request,
	"trusted_issuers": {},
	"policy_data": policy_data,
}

# What an inference module sees: the requester, and the script they bring.
inference_input(user_credentials, script_credentials, policy_data, request) := {
	"presentations": {
		"User": numbered(user_credentials, 0),
		"Script": numbered(script_credentials, count(user_credentials)),
	},
	"holders": {"User": requester, "Script": script},
	"request": request,
	"trusted_issuers": {},
	"policy_data": policy_data,
}
