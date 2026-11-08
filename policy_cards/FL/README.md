# FL — cards for federated inference

The cards in the parent folder can be attached to any guardian: they read facts
about the requester. These read facts about the **script** a requester brings to an
inference guardian, where the data stays put and code is run against it in place.
Approving a requester says nothing about the code, so these cards use a second
role:

- **`User`** — facts about the requester, presented from their wallet.
- **`Script`** — facts about the code, presented from the script asset itself.

A script is an asset behind a public guardian, and the identity chosen for the
`Script` role *is* that asset: the credentials about the code are presented from
it, and its DID resolves through the asset registry to the guardian it can be
fetched from.

## The cards

- **FL-DS** — [`inference-disease-specific-research/`](inference-disease-specific-research/)
  governs what the code declares it is for. Uses `Script` only, so a site carrying
  it alone never asks who is requesting.
- **FL-IS** — [`inference-institution-specific-restriction/`](inference-institution-specific-restriction/)
  governs who may run code here and that they stand behind it. Uses `User` and
  `Script`.

Which script runs is not theirs to say: the [inference delivery
module](../delivery/inference/) authorizes the digest of the `Script` holder, and
the webapp names the digest of the script it actually sends in
`request.script_digest`. Every module reads facts about the same holders, so the
use FL-DS approves, the ownership FL-IS checks and the digest the delivery module
authorizes are all about one script.

## Self-issued ownership

FL-IS is the card whose evidence is not all from registered authorities. The
`ScriptOwnershipCredential` is signed by the requester's own wallet -- a wallet
asserting "this script is mine". On its own that is worth nothing, so the card
checks its signature against the verifying key carried by a
`WalletVerifyingKeyCredential`, which *is* from a registered authority.

The wallet signs with `sign_with_contract_key`, the key PDO generates for every
contract and the ledger records in its metadata -- the same key the
`wallet_key_authority` reads off the ledger and attests. The card hands it to the
contract in `vc_supplied_verification_tasks`, and the contract checks the
signature against it directly.

## Each site chooses for itself

Each data holder attaches its own policy agent to its own asset, with its own
parameters, its own accepted authorities, and its own choice of cards. A round
over several sites asks each of them separately. In [the inference
tutorial](../../docs/docs/tutorial_inference.md), Hospital A carries FL-DS alone
and Hospital B carries FL-DS and FL-IS; the requester satisfies the union of what
the two ask for, and B's extra demands never reach A.

## Testing

```bash
../run_tests.sh
```

runs each card's unit tests and, in `tests/test_policy_cards.py`, both FL cards on
one inference site with the delivery module, merged the way the policy agent merges
them. Both are also exercised end to end through the web UI by
`tools/tests/run_webui_inference_test.sh`.
