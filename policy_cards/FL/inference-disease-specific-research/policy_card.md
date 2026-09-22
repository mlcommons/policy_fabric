# Policy Card — FL-DS (Disease Specific Research, inference)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.fl.inference-0000007-ds`
- **version:** 1.1.0
- **status:** draft
- **title:** Disease Specific Research for inference (FL-DS)
- **description:** Permit an inference run over the dataset when the script to be
  run declares an intended use within the owner's allowed diseases and states the
  digest identifying it.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for federated inference.
- **target.operations:** `inference`.
- **Out of scope:** what the requester does with the metrics an inference run
  returns.

## 3  Version History

| Version | Date       | Author    | Status | Summary of change                                                |
|---------|------------|-----------|--------|------------------------------------------------------------------|
| 1.0.0   | 2026-08-20 | MLCommons | draft  | Initial card, adapting DUO_0000007 DS to inference runs.         |
| 1.1.0   | 2026-08-23 | MLCommons | draft  | Require the declared use and the digest to name the same script. |

## 4  Summary & Intent

The dataset stays where it is and a script is run against it in place. What has to
declare a purpose is therefore the script, not a project the requester belongs to:
the script presents an `IntendedDataUseCredential` whose declared diseases intersect
the owner's allowed list, and a `ScriptHashCredential` giving its content digest.

Both credentials must be about the same script. A declaration of intended use is
only meaningful for the code it describes, so pairing an in-scope declaration with
the digest of some other script must not open the dataset.

- **Governance objective:** restrict inference over the asset to scripts whose
  declared use falls within an approved set of diseases.

## 5  Declarative Representation

```text
Permission: run inference over the target dataset
  Assignee:  the requester presenting the script's credentials
  Conditions (all must hold):
    - an IntendedDataUseCredential declares at least one disease ∈ allowedDiseases
    - a ScriptHashCredential gives the digest of the script to be run
    - both credentials name the same script as their subject
  On grant:  a capability naming the approved script digest
  Otherwise: denied
```

## 6  Associated Credentials

| Credential type             | Claims consumed       | Required |
|-----------------------------|-----------------------|----------|
| `IntendedDataUseCredential` | `useOnlyFor.diseases` | yes      |
| `ScriptHashCredential`      | `scriptHash`          | yes      |

Both credentials describe the script and must share one subject — the script's
identifier.

## 7  Reference Values Schema

```json
{
  "allowedDiseases": ["list of MONDO disease codes"]
}
```

- `allowedDiseases` — the MONDO disease codes this asset may be used to study. A
  declared use qualifies if any of its diseases appears in this list.

## 8  Capability Granted

```json
{
  "name": "do_inference",
  "parameters": {
    "script_digest": "<approved script digest>"
  }
}
```

- `script_digest` — the digest of the approved script, taken from the
  `ScriptHashCredential`. The Asset Guardian compares it against the code actually
  presented for execution, so a capability granted for one script cannot be used to
  run another.

## 9  Codified Representation

The executable rules are in [`policy.rego`](policy.rego), with unit tests in
[`policy_test.rego`](policy_test.rego). The module allows when one script both
declares an allowed disease and states the digest identifying it.

## 10  Legal & Disclaimers

- **Reference implementation.** This card is part of a demonstration of the
  Policy Fabric decoupling architecture and ships without warranty.
- **Scope.** The card governs the access decision only. It makes no claim about
  what happens to results after an inference run, and adopting it does not by
  itself establish conformance with any external requirement.
