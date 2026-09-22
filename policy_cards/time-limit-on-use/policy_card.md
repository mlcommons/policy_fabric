# Policy Card — DUO_0000025 TS (Time Limit on Use)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000025-ts`
- **version:** 1.0.0
- **status:** released
- **title:** Time Limit on Use (DUO_0000025 TS)
- **description:** Grant access only for a bounded period: the requester must
  accept the required terms and run on a compute environment attested to shut down
  no later than the policy deadline.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.operations:** `download`.
- **Out of scope:** any control over the asset after it is delivered
  (redistribution, retention).

## 3  Version History

| Version | Date       | Author                        | Status   | Summary of change                                      |
|---------|------------|-------------------------------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the TS policy.       |

## 4  Summary & Intent

Access to the dataset is limited to a defined time period. The requester presents
an `AgreementCredential` accepting the `requiredDocumentID` the data owner
configured, together with a `publicKeyCredential` carrying the delivery key; both
are issued to the **same subject**. A `ComputeEnvironmentCredential` must attest
that the compute environment shuts down no later than the `notAfter` deadline, so
use of the data cannot continue past that time.

- **Governance objective:** restrict download of the asset to requesters who
  accept the terms and run in a compute environment that shuts down by the
  configured deadline.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the AgreementCredential / publicKeyCredential)
  Conditions (all must hold):
    - an AgreementCredential accepts the required terms document (agreementInfo.documentID = requiredDocumentID)
    - a publicKeyCredential provides the requester's delivery key (claim: key), same subject as the agreement
    - a ComputeEnvironmentCredential attests hasComputeProfile.profile.shutsDownAt ≤ notAfter
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type              | Claims consumed                          | Required |
|------------------------------|------------------------------------------|----------|
| `AgreementCredential`        | `agreementInfo.documentID`               | yes      |
| `ComputeEnvironmentCredential` | `hasComputeProfile.profile.shutsDownAt`  | yes      |
| `publicKeyCredential`        | `key`                                    | yes      |

The agreement and public-key credentials are issued to the same subject (the
requester); the compute-environment credential attests the node the work runs on.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "requiredDocumentID": "DID of the terms document the requester must accept",
  "notAfter": "ISO-8601 datetime after which use is no longer permitted"
}
```

- `requiredDocumentID` — the terms document the requester's `AgreementCredential`
  must accept (as it appears in `AgreementCredential.agreementInfo.documentID`).
- `notAfter` — the latest permitted compute-environment shutdown time, compared
  against `ComputeEnvironmentCredential.hasComputeProfile.profile.shutsDownAt`.

## 8  Capability Granted

On success the card grants the operation below, which the Asset Guardian
enforces without interpreting policy logic:

```json
{
  "operation": {
    "name": "do_download",
    "parameters": { "channel_key": "<requester public key>" }
  }
}
```

- **operation:** `do_download` — the guardian operation invoked on success.
- **parameters.channel_key:** the `key` claim of the requester's
  `publicKeyCredential`; the guardian encrypts the delivered data to it.

## 9  Codified Representation

The policy is codified in Rego: [`policy.rego`](policy.rego), with unit tests in
[`policy_test.rego`](policy_test.rego). It evaluates to allow when the same subject
holds an `AgreementCredential` accepting the required terms and a
`publicKeyCredential`, and a `ComputeEnvironmentCredential` attests a shutdown time
no later than `notAfter`, and returns the granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
