# Policy Card — DUO_0000007 DS (Disease Specific Research)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000007-ds`
- **version:** 1.0.0
- **status:** released
- **title:** Disease Specific Research (DUO_0000007 DS)
- **description:** Grant access only when a project's intended-use approval limits
  the research to a disease within the data owner's allowed scope, and the
  requester is bound to that project as a member of the owning PI's team.
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
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the DS policy.       |

## 4  Summary & Intent

Access to the dataset is limited to research on an approved disease. A project's
`IntendedDataUseCredential` declares the diseases (as MONDO codes) the project is
approved to study; access is granted only when at least one of those diseases is
in the `allowedDiseases` set the data owner configured. The requester is tied to
the project through a chain: their `TeamCredential` names the PI whose
`ProjectOwnershipCredential` names the project the `IntendedDataUseCredential` is
about. The requester's `TeamCredential`, `AgreementCredential`, and
`publicKeyCredential` are issued to the **same subject**, so a single party is on
the team, has accepted the terms, and owns the key the data is encrypted to.

- **Governance objective:** restrict download of the asset to projects whose
  approved intended use falls within an allowed disease area.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the TeamCredential / AgreementCredential / publicKeyCredential)
  Conditions (all must hold):
    - an IntendedDataUseCredential declares  useOnlyFor.diseases ∩ allowedDiseases ≠ ∅
    - a ProjectOwnershipCredential shows a PI owns that project (Owns)
    - a TeamCredential places the requester on that PI's team (MemberOfTeamOf)
    - the requester presents an AgreementCredential (accepted terms)
    - a publicKeyCredential provides the requester's delivery key (claim: key)
    - the team, agreement, and public-key credentials share one subject
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type              | Claims consumed          | Required |
|------------------------------|--------------------------|----------|
| `IntendedDataUseCredential`  | `useOnlyFor.diseases`    | yes      |
| `ProjectOwnershipCredential` | `Owns`                   | yes      |
| `TeamCredential`             | `MemberOfTeamOf`         | yes      |
| `AgreementCredential`        | `agreementInfo`          | yes      |
| `publicKeyCredential`        | `key`                    | yes      |

The team, agreement, and public-key credentials must be issued to the same
subject (the requester); the ownership and intended-use credentials link that
requester's PI to the governed project.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "allowedDiseases": ["list of MONDO disease codes"]
}
```

`allowedDiseases` is the set of MONDO disease codes (as they appear in
`IntendedDataUseCredential.useOnlyFor.diseases`) for which access is permitted.

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
[`policy_test.rego`](policy_test.rego). It evaluates to allow when a project's
intended-use diseases intersect the allowed scope and the ownership/team chain
binds the requester to that project, and returns the granted operation of
section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
