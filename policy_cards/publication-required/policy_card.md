# Policy Card — DUO_0000019 PUB (Publication Required)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000019-pub`
- **version:** 1.0.0
- **status:** released
- **title:** Publication Required (DUO_0000019 PUB)
- **description:** Grant access only when an executed publication agreement binds
  the requester's institution to the governed dataset, and the requester is a
  member of the team of a PI affiliated with that institution.
- **author:** MLCommons
- **contact:** —

## 2  Scope & Target

- **target.asset:** the dataset the data owner exposes for controlled access.
- **target.operations:** `download`.
- **Out of scope:** any control over the asset after it is delivered
  (redistribution, retention), including whether results are ultimately published.

## 3  Version History

| Version | Date       | Author                        | Status   | Summary of change                                      |
|---------|------------|-------------------------------|----------|--------------------------------------------------------|
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the PUB policy.      |

## 4  Summary & Intent

Access to the dataset requires a publication agreement to be in place. The
requester is tied to a project and institution through a chain: their
`TeamCredential` names a PI whose `ProjectOwnershipCredential` names a project and
whose `AffiliationCredential` names an institution. A `ScopedAgreementCredential`
identifies a terms document scoped to that project carrying the `Publication`
obligation for the governed dataset, and an `AgreementCredential` shows the
institution has agreed to that document. Access is granted only when the whole
chain resolves to a single requester who also presents the delivery key.

- **Governance objective:** restrict download of the asset to requesters whose
  institution has executed a publication agreement covering the dataset.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the TeamCredential / publicKeyCredential)
  Conditions (all must hold):
    - a TeamCredential places the requester on a PI's team (MemberOfTeamOf)
    - a ProjectOwnershipCredential shows that PI owns a project (Owns)
    - an AffiliationCredential shows that PI belongs to an institution (isMemberOf)
    - a ScopedAgreementCredential scopes a terms document to that project with obligation = Publication and dataset = datasetID
    - an AgreementCredential shows the institution agreed to that terms document (agreementInfo.documentID)
    - a publicKeyCredential provides the requester's delivery key (claim: key)
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type              | Claims consumed                              | Required |
|------------------------------|----------------------------------------------|----------|
| `ProjectOwnershipCredential` | `Owns`                                       | yes      |
| `AffiliationCredential`      | `isMemberOf`                                 | yes      |
| `TeamCredential`             | `MemberOfTeamOf`                             | yes      |
| `ScopedAgreementCredential`  | `agreementInfo.scope` (obligation, project, dataset) | yes      |
| `AgreementCredential`        | `agreementInfo.documentID`                   | yes      |
| `publicKeyCredential`        | `key`                                        | yes      |

The team and public-key credentials share the requester's subject; the ownership,
affiliation, scoped-agreement, and agreement credentials link that requester's PI,
institution, and the governed dataset to the publication terms.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "datasetID": "DID of the governed dataset"
}
```

`datasetID` is the identifier of the dataset the publication agreement must be
scoped to (as it appears in `ScopedAgreementCredential.agreementInfo.scope.dataset`).

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
[`policy_test.rego`](policy_test.rego). It evaluates to allow when a publication
agreement scoped to the governed dataset ties the requester's institution to the
project the requester's PI owns, and returns the granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
