# Policy Card — DUO_0000028 IS (Institution Specific Restriction)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000028-is`
- **version:** 1.0.0
- **status:** released
- **title:** Institution Specific Restriction (DUO_0000028 IS)
- **description:** Grant access only when the requester presents a trusted
  `AffiliationCredential` naming a data-owner–approved institution, together with
  a `publicKeyCredential` carrying the public key their data is delivered to.
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
| 1.0.0   | 2026-07-10 | MLCommons                     | released | Initial policy card authored from the IS policy.       |

## 4  Summary & Intent

Access to the dataset is limited to requesters affiliated with an allowed
institution. The requester presents an `AffiliationCredential` whose `isMemberOf`
names one of the `allowedInstitutions` the data owner configured, together with a
`publicKeyCredential` carrying the public key their data is delivered to. Both
credentials must be issued to the **same subject**, so a single party both proves
the affiliation and owns the key the data is encrypted to.

- **Governance objective:** restrict download of the asset to members of
  approved institutions.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (the subject of the presented credentials)
  Conditions (all must hold):
    - an AffiliationCredential asserts  isMemberOf ∈ allowedInstitutions
    - a publicKeyCredential provides the requester's delivery key (claim: key)
    - both credentials are issued to the same subject
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type         | Claims consumed | Required |
|-------------------------|-----------------|----------|
| `AffiliationCredential` | `isMemberOf`    | yes      |
| `publicKeyCredential`   | `key`           | yes      |

Both credentials must be issued to the same subject.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "allowedInstitutions": ["list of strings"]
}
```

`allowedInstitutions` is the set of institution identifiers (as they appear in
`AffiliationCredential.isMemberOf`, i.e. institution DIDs) for which access is
permitted.

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
[`policy_test.rego`](policy_test.rego). It evaluates to allow when the same
subject holds both an approved `AffiliationCredential` and a
`publicKeyCredential`, and returns the granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
