# DUO policies (Rego) for the `rego_policy_agent` contract

Each DUO is one Rego module plus a human-readable `README.md`. A data owner
selects one or more DUOs when exposing an asset; the webapp creates a
`rego_policy_agent` contract and provisions the selected modules into it with
`set_rego_policy` (as `[ [ duo_id, rego_source ], ... ]`). The contract evaluates
each selected module and combines the results.

Policies may be grouped in a subfolder; [`FL/`](FL/) holds the ones written for
**inference**, where the data stays put and a script is run against it in place
instead of being downloaded. Those use a second role, `Script`, for evidence about
the code, and are documented in that folder's own README. Everything below concerns
the download DUOs at this level.

## Folders

Every DUO additionally requires a **publicKeyCredential** whose claim `key` is the
requester's channel public key; the module returns that key as the merged context
so the `rego_token` can hand it to the guardian. The tables below list the evidence
each DUO needs *in addition* to that key.

**Requester-attribute constraint** — one credential about the requester:

| DUO             | Folder         | Additional evidence        |
|-----------------|----------------|----------------------------|
| DUO_0000022 GS  | [`geographical-restriction/`](geographical-restriction/)   | LocationCredential         |
| DUO_0000028 IS  | [`institution-specific-restriction/`](institution-specific-restriction/)   | AffiliationCredential      |
| DUO_0000026 US  | [`user-specific-restriction/`](user-specific-restriction/)   | UserPlatformCredential     |
| DUO_0000045 NPU | [`not-for-profit-organisation-use-only/`](not-for-profit-organisation-use-only/) | LegalDesignationCredential |

**Intended-use constraint** — a project `IntendedDataUseCredential` bound to the
requester through `ProjectOwnershipCredential` + `TeamCredential`, plus an
`AgreementCredential`; the DUOs differ only in the check on the intended use:

| DUO              | Folder           | Check on the intended use                  |
|------------------|------------------|--------------------------------------------|
| DUO_0000007 DS   | [`disease-specific-research/`](disease-specific-research/)     | diseases within an allowed MONDO scope     |
| DUO_0000006 HMB  | [`health-or-medical-or-biomedical-research/`](health-or-medical-or-biomedical-research/)   | health/medical/biomedical purpose, not POA |
| DUO_0000016 GSO  | [`genetic-studies-only/`](genetic-studies-only/)   | genetic-studies purpose                    |
| DUO_0000012 RS   | [`research-specific-restrictions/`](research-specific-restrictions/)     | purpose within an allowed research scope   |
| DUO_0000011 POA  | [`population-origins-or-ancestry-research-only/`](population-origins-or-ancestry-research-only/)   | population-origins/ancestry purpose        |
| DUO_0000015 NMDS | [`no-general-methods-research/`](no-general-methods-research/) | no methods-development purpose             |
| DUO_0000046 NCU  | [`non-commercial-use-only/`](non-commercial-use-only/)   | no commercial purpose                      |
| DUO_0000044 NPOA | [`population-origins-or-ancestry-research-prohibited/`](population-origins-or-ancestry-research-prohibited/) | no population-origins/ancestry purpose     |
| DUO_0000027 PS   | [`project-specific-restriction/`](project-specific-restriction/)     | project on the owner's approved list       |

**Accepted-terms constraint** — an `AgreementCredential` accepting the required
terms document, plus (for MOR/RTN/TS) a `ComputeEnvironmentCredential`:

| DUO             | Folder         | Additional evidence                                   |
|-----------------|----------------|-------------------------------------------------------|
| DUO_0000042 GRU | [`general-research-use/`](general-research-use/) | —                                                     |
| DUO_0000024 MOR | [`publication-moratorium/`](publication-moratorium/) | ComputeEnvironmentCredential (secure handling)        |
| DUO_0000029 RTN | [`return-to-database-or-resource/`](return-to-database-or-resource/) | ComputeEnvironmentCredential (secure handling)        |
| DUO_0000025 TS  | [`time-limit-on-use/`](time-limit-on-use/)   | ComputeEnvironmentCredential (shutdown by a deadline) |

**Agreement-scope obligation** (`col`, `pub`) — `ProjectOwnershipCredential` +
`AffiliationCredential` + `TeamCredential` + `ScopedAgreementCredential` +
`AgreementCredential`, where the scoped agreement carries the `Collaboration`
(DUO_0000020 COL) or `Publication` (DUO_0000019 PUB) obligation for the dataset.

**Ethics approval** (`irb`, DUO_0000021) — `IntendedDataUseCredential` +
`IRBApprovalCredential` + `ProjectOwnershipCredential` +
`EthicsCommitteeAccreditationCredential` + `AffiliationCredential` +
`TeamCredential`: the project is approved by a committee responsible for the
requester's institution.

**Not-for-profit + non-commercial** (`npuncu`, DUO_0000018) —
`LegalDesignationCredential` (non-profit legal form) + `IntendedDataUseCredential`
(no commercial purpose).

## The contract <-> Rego contract

Every module is package `subpolicy` and exposes the two rules the
`rego_policy_agent` evaluates, each in its own regorus engine (lowest peak
memory; also why the identical package/rule names never collide).

**`data.subpolicy.requirements`** — evaluated by `set_rego_policy` with **no
input**, so it must be static. The roles and credential types this module needs:

```json
{ "User": ["LocationCredential", "publicKeyCredential"] }
```

**`data.subpolicy.result`** — evaluated by `issue_policy_credential` over the
input the contract builds:

```json
{
  "presentations": {
    "<role>": [
      { "type": "<CredentialType>", "issuer": "<did>", "subject": "<did>",
        "claims": { ... }, "index": <int> }
    ]
  },
  "trusted_issuers": { ... },
  "policy_data": { ... }
}
```

and produces:

```json
{
  "decision": true,
  "verification_tasks": [ { "index": <int> } ],
  "operation": { "name": "do_download", "parameters": { "channel_key": "<requester public key>" } }
}
```

- Presentations arrive as `{ role: VerifiablePresentation }`; the contract
  flattens each role's credentials into the array above and assigns each a global
  `index`. A `verification_task` references that index so the contract verifies
  the exact VC's signature against the registered trusted issuer.
- `decision` is a boolean. When several DUOs are selected the contract allows
  only if **every** module allowed, verifies the union of the flagged
  credentials (a failed signature forces a deny), and merges the operations.
- `operation` is `{ "name": <operation>, "parameters": { ... } }`; it is merged
  across modules and becomes the claims of the issued `policy_decision`
  credential. The `rego_token` parses it to build the guardian capability: `name`
  is the guardian operation to invoke (`do_download`) and `parameters` (the
  `channel_key`) are forwarded to it.

## Tests

```bash
./run_tests.sh        # runs `opa test` on each DUO folder independently
```

Each folder is tested on its own because all modules share package `subpolicy`;
compiling them together would be a redefinition conflict (which is exactly why
the contract isolates them per engine).
