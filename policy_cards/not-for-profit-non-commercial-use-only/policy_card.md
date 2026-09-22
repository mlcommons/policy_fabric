# Policy Card — DUO_0000018 NPUNCU (Not-for-Profit, Non-Commercial Use Only)

Authored against the Policy Fabric Policy Card template (`duos/policy_schema.txt`).

---

## 1  Identification

- **id:** `card.duo.0000018-npuncu`
- **version:** 1.0.0
- **status:** released
- **title:** Not-for-Profit, Non-Commercial Use Only (DUO_0000018 NPUNCU)
- **description:** Grant access only when the requester's organization has a
  not-for-profit legal form and the project's intended use declares no commercial
  purpose.
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
| 1.0.0   | 2026-07-15 | MLCommons                     | released | Initial policy card authored from the NPUNCU policy.   |

## 4  Summary & Intent

Access to the dataset is limited to not-for-profit organizations pursuing a
non-commercial use. The requester presents a `LegalDesignationCredential` whose
`hasLegalForm` is one of the `nonprofitLegalForms` the data owner configured,
together with a `publicKeyCredential` carrying the delivery key; both are issued to
the **same subject**. The project's `IntendedDataUseCredential` must declare no
purpose in the data owner's `prohibitedPurposes` (e.g. commercial use).

- **Governance objective:** restrict download of the asset to not-for-profit
  organizations whose declared intended use is non-commercial.

## 5  Declarative Representation

```text
Permission: download the target dataset
  Assignee:  the requester (subject of the LegalDesignationCredential / publicKeyCredential)
  Conditions (all must hold):
    - a LegalDesignationCredential asserts  hasLegalForm ∈ nonprofitLegalForms
    - an IntendedDataUseCredential declares  useOnlyFor.purposes ∩ prohibitedPurposes = ∅
    - a publicKeyCredential provides the requester's delivery key (claim: key)
    - the legal designation and public-key credentials are issued to the same subject
  On grant:  operation "do_download", with the data encrypted to that key
  Otherwise: deny
```

## 6  Associated Credentials (Evidence Requirements)

Every type resolves to a schema in [`../../credentials/`](../../credentials/).

| Credential type              | Claims consumed          | Required |
|------------------------------|--------------------------|----------|
| `LegalDesignationCredential` | `hasLegalForm`           | yes      |
| `IntendedDataUseCredential`  | `useOnlyFor.purposes`    | yes      |
| `publicKeyCredential`        | `key`                    | yes      |

The legal-designation and public-key credentials are issued to the same subject
(the requester); the intended-use credential declares the project's purposes.

## 7  Reference Values Schema

Reference values the data owner configures (see
[`policy_data_schema.json`](policy_data_schema.json)):

```json
{
  "nonprofitLegalForms": ["list of not-for-profit ISO 20275 ELF codes"],
  "prohibitedPurposes": ["list of prohibited purpose terms"]
}
```

- `nonprofitLegalForms` — ISO 20275 ELF codes (as they appear in
  `LegalDesignationCredential.hasLegalForm`) the data owner treats as not-for-profit.
- `prohibitedPurposes` — purpose terms (as they appear in
  `IntendedDataUseCredential.useOnlyFor.purposes`) that make the use commercial and
  therefore disqualifying.

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
holds a not-for-profit `LegalDesignationCredential` and a `publicKeyCredential`,
and a project `IntendedDataUseCredential` declares no prohibited purpose, and
returns the granted operation of section 8.

## 10  Legal & Disclaimers

Reference-implementation status: this card and its Rego policy are a reference
implementation provided as-is. You are responsible for verifying its accuracy and
fitness for your use case before relying on it — it is not a certified or legally
reviewed compliance control. Do not use this card or policy to protect sensitive
data (e.g., health, medical, genetic, or other legally regulated personal data)
without independent legal and security review.
