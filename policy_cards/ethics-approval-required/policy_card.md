# Policy Card — DUO_0000021 IRB (Ethics Approval Required)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000021-irb`
- **version:** 1.0.0
- **status:** released
- **title:** Ethics Approval Required (DUO_0000021 IRB)
- **description:** Grant access only when the project holds ethics approval from a
  committee responsible for the institution of the PI whose team the requester is
  on.
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
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the IRB policy.      |

## 4  Summary & Intent

Access to the dataset requires ethics (IRB) approval for the research project. The
requester is tied to a project and institution through a chain: their
`TeamCredential` names a PI whose `ProjectOwnershipCredential` names a project and
whose `AffiliationCredential` names an institution. An `IRBApprovalCredential`
shows the project is approved by an ethics committee, and an
`EthicsCommitteeAccreditationCredential` shows that committee is responsible for
the PI's institution — so the approval comes from the body that oversees the
requester's own institution. The project's `IntendedDataUseCredential` declares
its intended use. Access is granted only when the whole chain resolves to a single
requester who also presents the delivery key.

- **Governance objective:** restrict download of the asset to projects that hold
  ethics approval from the committee responsible for the requester's institution.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the TeamCredential / publicKeyCredential)
  Conditions (all must hold):
    - a TeamCredential places the requester on a PI's team (MemberOfTeamOf)
    - a ProjectOwnershipCredential shows that PI owns a project (Owns)
    - an AffiliationCredential shows that PI belongs to an institution (isMemberOf)
    - an IRBApprovalCredential shows that project is approved by an ethics committee (isApprovedByEthicsCommittee)
    - an EthicsCommitteeAccreditationCredential shows that committee is responsible for that same institution (ResponsibleFor)
    - an IntendedDataUseCredential declares the project's intended use
    - a publicKeyCredential provides the requester's delivery key (claim: key)
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type                          | Claims consumed              | Required |
|------------------------------------------|------------------------------|----------|
| `IntendedDataUseCredential`              | `useOnlyFor`                 | yes      |
| `IRBApprovalCredential`                  | `isApprovedByEthicsCommittee`| yes      |
| `ProjectOwnershipCredential`             | `Owns`                       | yes      |
| `EthicsCommitteeAccreditationCredential` | `ResponsibleFor`             | yes      |
| `AffiliationCredential`                  | `isMemberOf`                 | yes      |
| `TeamCredential`                         | `MemberOfTeamOf`             | yes      |
| `publicKeyCredential`                    | `key`                        | yes      |

The team and public-key credentials share the requester's subject; the ownership,
affiliation, approval, and accreditation credentials link that requester's PI,
institution, project, and the approving ethics committee.

## 7  Reference Values Schema

This policy requires no owner-configured reference values; the decision is
structural (see [`policy_data_schema.json`](policy_data_schema.json)):

```json
{}
```

The ethics-approval chain must be internally consistent — the committee that
approved the project must be the one responsible for the requester's institution —
so no external allow-list is consulted.

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
[`policy_test.rego`](policy_test.rego). It evaluates to allow when the project's
ethics approval comes from a committee responsible for the requester's institution
and the ownership/team chain binds the requester to that project, and returns the
granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
