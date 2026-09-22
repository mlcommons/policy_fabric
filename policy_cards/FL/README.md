# FL — policies for federated inference

The DUOs in the parent folder govern **download**: the data leaves, encrypted to
the requester's channel key. These govern **inference**: the data stays put and a
script is run against it in place.

That changes what the evidence has to cover. A download policy answers *who is
asking*; an inference policy also has to answer *what is going to run*, because
approving a requester says nothing about the code they bring. So these policies use
two roles:

- **`User`** — credentials about the requester (their institution, their channel
  key, their wallet key).
- **`Script`** — credentials about the code (its digest, who owns it, what it
  declares it is for).

The two roles are separate because they describe different subjects and are
presented from different identities. Every credential in `Script` is about a script
asset, named by its DID.

A script is itself an asset, registered behind a public guardian, and the identity
chosen for the `Script` role *is* that asset. One choice settles two things: the
credentials about the code are presented from it, and its DID resolves through the
asset registry to the public guardian the script can be fetched from — which is how
the runner gets the code to hand to the FL server.

## The policies

Each policy stands on its own and is selected on its own merits.

- **FL-IS** — [`inference-institution-specific-restriction/`](inference-institution-specific-restriction/)
  governs who may run code here and that they stand behind it. Uses `User` and
  `Script`.
- **FL-DS** — [`inference-disease-specific-research/`](inference-disease-specific-research/)
  governs what the code declares it is for. Uses `Script` only.

Each adapts the same-named DUO in the parent folder. FL-IS keeps the institution
constraint and adds the tie between requester and script; FL-DS keeps the disease
scope and moves the declaration onto the script, since that is what runs.

## Self-issued ownership

FL-IS is the first policy here whose evidence is not all issued by registered
authorities. The `ScriptOwnershipCredential` is signed by the requester's own
wallet — a wallet asserting "this script is mine". On its own that is worth
nothing, so the policy checks its signature against the verifying key carried by a
`WalletVerifyingKeyCredential`, which *is* from a registered authority. That is
what turns a self-assertion into something a policy can rely on, and it is the
mechanism the parent DUOs never needed.

Concretely, the wallet signs with `sign_with_contract_key` — the key PDO generates
for every contract and the ledger records in that contract's metadata. That is the
same key the `wallet_key_authority` reads off the ledger and puts in the
`WalletVerifyingKeyCredential`, which is why the two line up. The policy hands the
key back to the contract in `vc_supplied_verification_tasks`, and the contract
checks the signature against it directly instead of walking a registered issuer's
key tree.

## Testing

```bash
opa test inference-institution-specific-restriction -v
opa test inference-disease-specific-research -v
./run_combination_test.sh
```

A data owner may select any set of policies for one asset, and the contract merges
what they return: the request is allowed only if every selected policy allowed, and
their operations are merged into one capability.
`run_combination_test.sh` checks that merge for the policies here by evaluating each
in isolation and then combining the results the way `rego_policy_agent` does — the
only way to exercise it without deploying the contract.

Both policies are also exercised against a live deployment, end to end through the
web UI, by `tools/tests/run_webui_inference_test.sh` — the automation of
[the inference tutorial](../../docs/docs/tutorial_inference.md), whose two parts
are FL-DS and FL-IS.

## Each site chooses for itself

Nothing about these policies is federation-wide, and that is the point. Each data
holder attaches its own policy agent contract to its own asset, with its own
policy data, its own trusted issuers, and its own choice of *which* of these
policies to apply — one, the other, or both. A round over several sites asks each
of them separately and gets a separate verdict.

The tutorial is exactly that: Hospital A attaches FL-DS alone and never asks who
is requesting; Hospital B attaches FL-DS **and** FL-IS to one asset and does. One
round serves both, and the requester has to satisfy the union of what the two
sites ask for — `Script` alone would not get past B, and B's extra demands never
reach A.
