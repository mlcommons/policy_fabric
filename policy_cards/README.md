# Policy cards

A policy card states what must be true to use an asset. It names the **facts** it
needs -- standard credentials about the holder of a role -- and the rule over them.
It does not say how a fact is established, whom to trust for it, or how the asset is
delivered:

| Decision | Made by | Lives in |
|----------|---------|----------|
| What must be true to use my data | the data owner | a policy card and its parameters |
| Whose word I accept, per fact | the data owner | the trusted issuers of the asset's policy agent |
| How a fact is established | an authority's operator | an [authority](../authority_cards/) |
| What is unlocked, and how | the platform, per guardian type | a [delivery module](delivery/) |

A data owner selects one or more cards when exposing an asset. The webapp provisions
them, plus the delivery module of the asset's guardian, into one `rego_policy_agent`
as `[ [ module_id, rego_source ], ... ]`. The agent evaluates each module in its own
engine; it allows only if every module allows.

## Folders

Every card folder holds a `card.json` manifest, a `README.md` shown to owners, a
`policy_card.md` (the full Policy Card), and its rule: its own `policy.rego` with
`policy_test.rego`, or a [rule template](templates/) named by the manifest.

**One fact about the requester, one claim on an allow-list:**

| Card | Folder | Fact |
|------|--------|------|
| DUO_0000022 GS  | [`geographical-restriction/`](geographical-restriction/) | LocationCredential |
| DUO_0000028 IS  | [`institution-specific-restriction/`](institution-specific-restriction/) | AffiliationCredential |
| DUO_0000026 US  | [`user-specific-restriction/`](user-specific-restriction/) | UserPlatformCredential |
| DUO_0000045 NPU | [`not-for-profit-organisation-use-only/`](not-for-profit-organisation-use-only/) | LegalDesignationCredential |

**The requester's research purpose** (a `ResearchPurposeCredential`, which the
[project research purpose](../authority_cards/project-research-purpose/) authority
can issue from the requester's team, PI and project):

| Card | Folder | Rule |
|------|--------|------|
| DUO_0000007 DS    | [`disease-specific-research/`](disease-specific-research/) | a disease within the owner's MONDO scope |
| DUO_0000006 HMB   | [`health-or-medical-or-biomedical-research/`](health-or-medical-or-biomedical-research/) | an allowed purpose and no prohibited one |
| DUO_0000016 GSO   | [`genetic-studies-only/`](genetic-studies-only/) | template `purpose-allowed` |
| DUO_0000012 RS    | [`research-specific-restrictions/`](research-specific-restrictions/) | template `purpose-allowed` |
| DUO_0000011 POA   | [`population-origins-or-ancestry-research-only/`](population-origins-or-ancestry-research-only/) | template `purpose-allowed` |
| DUO_0000015 NMDS  | [`no-general-methods-research/`](no-general-methods-research/) | template `purpose-prohibited` |
| DUO_0000046 NCU   | [`non-commercial-use-only/`](non-commercial-use-only/) | template `purpose-prohibited` |
| DUO_0000044 NPOA  | [`population-origins-or-ancestry-research-prohibited/`](population-origins-or-ancestry-research-prohibited/) | template `purpose-prohibited` |
| DUO_0000027 PS    | [`project-specific-restriction/`](project-specific-restriction/) | a project on the owner's list |

**Obligations, ethics, and accepted terms:**

| Card | Folder | Facts |
|------|--------|-------|
| DUO_0000020 COL    | [`collaboration-required/`](collaboration-required/) | ObligationAcceptanceCredential |
| DUO_0000019 PUB    | [`publication-required/`](publication-required/) | ObligationAcceptanceCredential |
| DUO_0000021 IRB    | [`ethics-approval-required/`](ethics-approval-required/) | EthicsApprovalCredential |
| DUO_0000042 GRU    | [`general-research-use/`](general-research-use/) | AgreementCredential |
| DUO_0000024 MOR    | [`publication-moratorium/`](publication-moratorium/) | Agreement + ComputeEnvironment (template `secure-results`) |
| DUO_0000029 RTN    | [`return-to-database-or-resource/`](return-to-database-or-resource/) | Agreement + ComputeEnvironment (template `secure-results`) |
| DUO_0000025 TS     | [`time-limit-on-use/`](time-limit-on-use/) | Agreement + ComputeEnvironment |
| DUO_0000018 NPUNCU | [`not-for-profit-non-commercial-use-only/`](not-for-profit-non-commercial-use-only/) | LegalDesignation + ResearchPurpose |

**Inference** -- [`FL/`](FL/) holds the cards that read facts about the script a
requester brings, under a second role, `Script`.

The DUO cards read only facts about the requester, so they apply behind a download
and an inference guardian alike; each manifest lists its `guardianTypes`.

## The module contract

Every module -- card, template, delivery module or authority -- is `package
subpolicy` with two rules; the module that describes the credential to issue
declares a third.

**`data.subpolicy.requirements`**, evaluated with no input, so it must be static:
the roles and credential types the module reads, e.g. `{ "User":
["LocationCredential"] }`. A card's `facts` must equal it.

**`data.subpolicy.issues`**, static too, only in a delivery module or an
authority's rule: the type of credential the policy agent issues, e.g.
`"policy_decision"`. The agent reads it when the policy is set and refuses a
policy where no module, or more than one, declares it. Cards leave it out.

**`data.subpolicy.result`**, evaluated over:

```json
{
  "presentations": {
    "<role>": [
      { "type": "<CredentialType>", "issuer": "<did>", "signer": "<did>",
        "trusted": true, "subject": "<did>", "claims": { ... }, "index": 0 }
    ]
  },
  "holders": { "<role>": "<did of the role's presentation holder>" },
  "request": { "project": "<did>" },
  "trusted_issuers": { ... },
  "policy_data": { "<this module's parameters>" }
}
```

and returning:

```json
{ "decision": true, "verification_tasks": [ { "index": 0 } ], "vc_supplied_verification_tasks": [] }
```

- A fact counts only if it is about the holder of its role (`subject ==
  holders[role]`) and `trusted`: its issuer is its signer, and the policy agent
  trusts that signer for its type. A holder may carry several credentials of a
  type; flagging only trusted ones keeps a copy from an authority the owner does not
  accept from failing the request.
- `request` carries what the requester declares -- the project, the channel key,
  the script digest. A module requires the values it reads: a project-bound card
  denies unless its fact is about `request.project`, so every card on an asset
  agrees on the project without seeing the others.
- `policy_data` is `policy_data[module_id]`: each module reads only its own
  parameters, so two cards never share one `allowedPurposes`. The owner sets an
  entry for every module, `{}` for one with no parameters.
- `verification_tasks` flag credentials by global `index` for the contract to
  verify against their trusted issuer; `vc_supplied_verification_tasks` against a
  key the module supplies (see FL-IS). A failed signature denies.
- Cards describe no credential. The delivery module does, when it allows: the
  `policy_decision` the agent issues, `credential: {subject, claims: {name,
  parameters}}`, naming the guardian operation. A policy where no module describes
  it is denied, and the agent refuses a credential from a module that does not
  declare `issues`. A module that adds a credential to its result defines one
  result for allow and one for deny rather than placeholder defaults.

Rego engine note: the policy agent runs regorus. Keep comprehensions out of the
value of a rule that has a body (`x := {... [c | ...] ...} if cond`); compute them
as rules of their own.

## Tests

```bash
./run_tests.sh   # opa test per folder, then tests/test_policy_cards.py
```

Each folder is tested on its own (`opa test <folder> tests/testlib.rego`), since
every module is `package subpolicy`. [`tests/`](tests/) then checks, across cards:
manifests against [`card.schema.json`](card.schema.json) and against each rule's
requirements; that only delivery modules declare `issues`; every fact against the
credential vocabulary, about its role's
holder; parameter schemas and presets; that regorus agrees with opa on every
module; and cards combined on one asset, merged by a copy of the policy agent's
combinators. It needs `opa`, `regorus` (or `$OPA` and `$REGORUS`) and the
`jsonschema` Python package.
