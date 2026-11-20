# FL — cards for federated inference

The cards in the parent folder issue `do_download`. These issue **`do_inference`**, for an
inference guardian, where the data stays put and code is run against it in place.
Approving a requester says nothing about the code, so these cards read credentials about
the **script** a requester brings, under a second role:

- **`User`** — credentials about the requester, presented from their wallet.
- **`Script`** — credentials about the code, presented from the script asset itself.

A script is an asset behind a public guardian, and the identity chosen for the `Script`
role *is* that asset: the credentials about the code are presented from it, and its DID
resolves through the asset registry to the guardian it can be fetched from.

## The cards

- **FL-DS** — [`inference-disease-specific-research/`](inference-disease-specific-research/)
  governs what the code declares it is for. It reads only credentials about the script, so
  a site carrying it alone never asks who is requesting.
- **FL-IS** — [`inference-institution-specific-restriction/`](inference-institution-specific-restriction/)
  governs who may run code here and that they stand behind it. It reads credentials about
  the requester and about the script.

Each card component outputs a DataUseConditionCredential about the script. The graph's
capability issues `do_inference` for the digest the request names (`request.script_digest`,
the digest of the script the webapp actually sends) only when every card on the asset holds
for that script, and a `ScriptHashCredential` about the script, from an authority the owner
accepts, carries that digest.

## Self-issued ownership

FL-IS is the card whose evidence is not all from accepted authorities. The
`ScriptOwnershipCredential` is signed by the requester's own wallet -- a wallet asserting
"this script is mine". On its own that is worth nothing, so the card checks its signature
against the verifying key carried by a `WalletVerifyingKeyCredential`, which *is* from an
authority the owner accepts.

The wallet signs with `sign_with_contract_key`, the key PDO generates for every contract
and the ledger records in its metadata -- the same key the wallet key authority reads off
the ledger and attests. The component's input is marked `supplied_key`: its output names
that key for the ownership credential (`key_checks`), and the contract checks the
signature against it directly, instead of against a trusted issuer.

## Each site chooses for itself

Each data holder attaches its own policy agent to its own asset, with its own parameters,
its own accepted authorities, and its own choice of cards. A round over several sites asks
each of them separately. In [the inference tutorial](../../docs/docs/tutorial_inference.md),
Hospital A carries FL-DS alone and Hospital B carries FL-DS and FL-IS, composed into one
graph; the requester satisfies the union of what the two ask for, and B's extra demands
never reach A.

## Testing

[`../../policy_components/run_tests.sh`](../../policy_components/run_tests.sh) runs both
cards' graph tests, and `tools/tests/run_webui_inference_test.sh` runs them end to end through
the web UI.
