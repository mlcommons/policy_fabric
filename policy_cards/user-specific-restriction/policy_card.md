# Policy Card — DUO_0000026 US (User Specific Restriction)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000026-us`
- **version:** 1.0.0
- **status:** released
- **title:** User Specific Restriction (DUO_0000026 US)
- **description:** Grant access only when the requester's platform account meets at
  least one of the data owner's eligibility criteria (approved user, allowed
  account type, or required profile status).
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
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the US policy.       |

## 4  Summary & Intent

Access to the dataset is limited to eligible users. The requester presents a
`UserPlatformCredential` describing their platform account, together with a
`publicKeyCredential` carrying the public key their data is delivered to; both are
issued to the **same subject**. Access is granted when the account satisfies at
least one eligibility route the data owner configured — an approved user
identifier, an allowed account type, or a required profile status.

- **Governance objective:** restrict download of the asset to requesters whose
  platform account meets the configured eligibility criteria.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the presented credentials)
  Conditions (all must hold):
    - a UserPlatformCredential satisfies at least one route:
        userId ∈ approvedUsers  OR  accountType ∈ allowedAccountTypes  OR  profileStatus ∈ requiredProfileStatuses
    - a publicKeyCredential provides the requester's delivery key (claim: key)
    - both credentials are issued to the same subject
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type          | Claims consumed                       | Required |
|--------------------------|---------------------------------------|----------|
| `UserPlatformCredential` | `userId`, `accountType`, `profileStatus` | yes   |
| `publicKeyCredential`    | `key`                                 | yes      |

Both credentials must be issued to the same subject.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "approvedUsers": ["list of approved user identifiers"],
  "allowedAccountTypes": ["list of allowed account types"],
  "requiredProfileStatuses": ["list of accepted profile statuses"]
}
```

Each list is one eligibility route (matched against `UserPlatformCredential.userId`,
`.accountType`, and `.profileStatus` respectively); a requester qualifies by
satisfying any one of them.

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
holds a `UserPlatformCredential` satisfying an eligibility route and a
`publicKeyCredential`, and returns the granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
