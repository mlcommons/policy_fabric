# Authority cards

An authority establishes a fact. Policies name the facts they need; authorities
issue them as standard credentials; a data owner chooses, per fact, which
authorities to accept. Several authorities, built in very different ways, can issue
the same fact, and a policy never needs to know which one did:

| Kind | How it establishes a fact | Contract |
|------|---------------------------|----------|
| Hand-signing | a person or office signs after its own review | `signature_authority` |
| Rule-based | a Rego rule over input credentials, from issuers it trusts | `rego_policy_agent` |
| System | ledger or cryptographic facts, or an external system | the authority family (session keys, wallet keys) |

This folder holds the **rule-based** ones. An authority card has the same anatomy as
a policy card -- a `card.json`, a `policy.rego` in `package subpolicy`, its tests and
a README -- and runs in the same contract: a rule-based authority is a policy agent
whose one module, its rule, describes a fact rather than a policy decision. Its
result carries the credential to issue:

```json
{ "decision": true, "verification_tasks": [ ... ], "vc_supplied_verification_tasks": [],
  "credential": { "subject": "<did>", "claims": { ... } } }
```

The rule declares the type it issues, `issues := "<type>"`, which must be the
card's `issues`; the policy agent reads it when the rule is set and issues nothing
else. Its policy is set once and never changes, so trusting an authority
means trusting one auditable rule; its operator still decides whom it trusts for
its inputs.

| Authority | Issues | Moves out of the policies |
|-----------|--------|---------------------------|
| [`accredited-committee-check/`](accredited-committee-check/) | EthicsApprovalCredential | IRB's chain: team, PI, project, approving committee, accreditation |
| [`project-research-purpose/`](project-research-purpose/) | ResearchPurposeCredential | the DS/HMB/GSO/RS/POA/NMDS/NCU/NPOA/PS chain: team, PI, project, intended use |
| [`scoped-obligation-acceptance/`](scoped-obligation-acceptance/) | ObligationAcceptanceCredential | COL and PUB's chain: team, PI, institution, scoped agreement |

Each card says who presents its inputs (`presenters`). All three here take them from
the member's own wallet, where the issuing offices deliver copies of the credentials
about the member's PI, project and committee; the output lands in the same wallet.
A sponsored variant -- the PI presenting for a member -- would be another card.

## Tests

```bash
./run_tests.sh   # opa test per card, then policy_cards/tests/test_authority_cards.py
```

Beyond each card's unit tests: manifests against the card schema and the rule's
requirements, every issued type a standard fact about a holder, and the claims each
rule issues for a complete chain valid against that fact's JSON Schema -- the
contract checks only their shape. The shared builders live in
[`../policy_cards/tests/`](../policy_cards/tests/).
