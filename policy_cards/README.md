# Policy cards

A policy card states what must be true to use an asset. Each card is a **graph of
[policy components](../policy_components/)** (`graph.json`): small Rego components that
pass credentials to each other. Shared components join credentials into new ones --
ProjectMembership turns a requester's team and their PI's project ownership into a
ProjectMembershipCredential -- a card component checks the result against the owner's
parameters and outputs a grant, and Grant download or Grant inference issues the
capability the asset's guardian redeems.

| Decision | Made by | Lives in |
|----------|---------|----------|
| What must be true to use my data | the data owner | the cards' graphs, and each node's parameters |
| Whose word I accept, per credential type | the data owner | the trusted issuers of the asset's policy agent |
| How a credential is established | an authority's operator | an authority, on the webapp's Authorities page |
| What is unlocked, and how | the platform, per guardian type | Grant download or Grant inference |

A data owner selects one or more cards when exposing an asset. Their graphs compose into
one under a single grant, sharing the components they have in common, and the webapp sets
it on the asset's `rego_policy_agent` with `set_policy_graph`. The contract validates the
graph against its components' interfaces, plans per request which components run, runs
them, and issues the capability only after verifying every credential they read.

A credential a component produces can also be presented, when the card's graph accepts it
presented and an authority the owner accepts issued it: ProjectMembershipCredential and
IRBClearanceCredential (their schemas say `x-presentable`). A graph therefore lists every
bundle of credentials that satisfies it, its requirement alternatives, and a requester
presents one.

## Folders

Every card folder holds its `graph.json`, the `graph_vectors.json` that states the
decisions the graph must reach, a `card.json` with its code, name and one-line rule (see
[`card.schema.json`](card.schema.json)), the `README.md` shown to owners, and
`policy_card.md`, the full Policy Card.

| Card | Folder | Credentials it takes presented, besides the session key |
|------|--------|---------------------------------------------------------|
| DUO_0000020 COL | [`collaboration-required/`](collaboration-required/) | Accepted terms, Affiliation, Project membership, Project ownership, Scoped agreement, Team membership |
| DUO_0000007 DS | [`disease-specific-research/`](disease-specific-research/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000021 IRB | [`ethics-approval-required/`](ethics-approval-required/) | Affiliation, Ethics committee accreditation, IRB approval, IRB clearance, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000042 GRU | [`general-research-use/`](general-research-use/) | Accepted terms |
| DUO_0000016 GSO | [`genetic-studies-only/`](genetic-studies-only/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000022 GS | [`geographical-restriction/`](geographical-restriction/) | Location |
| DUO_0000006 HMB | [`health-or-medical-or-biomedical-research/`](health-or-medical-or-biomedical-research/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000028 IS | [`institution-specific-restriction/`](institution-specific-restriction/) | Affiliation |
| DUO_0000015 NMDS | [`no-general-methods-research/`](no-general-methods-research/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000046 NCU | [`non-commercial-use-only/`](non-commercial-use-only/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000018 NPUNCU | [`not-for-profit-non-commercial-use-only/`](not-for-profit-non-commercial-use-only/) | Intended data use, Legal designation |
| DUO_0000045 NPU | [`not-for-profit-organisation-use-only/`](not-for-profit-organisation-use-only/) | Legal designation |
| DUO_0000011 POA | [`population-origins-or-ancestry-research-only/`](population-origins-or-ancestry-research-only/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000044 NPOA | [`population-origins-or-ancestry-research-prohibited/`](population-origins-or-ancestry-research-prohibited/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000027 PS | [`project-specific-restriction/`](project-specific-restriction/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000024 MOR | [`publication-moratorium/`](publication-moratorium/) | Accepted terms, Compute environment |
| DUO_0000019 PUB | [`publication-required/`](publication-required/) | Accepted terms, Affiliation, Project membership, Project ownership, Scoped agreement, Team membership |
| DUO_0000012 RS | [`research-specific-restrictions/`](research-specific-restrictions/) | Accepted terms, Intended data use, Project membership, Project ownership, Team membership |
| DUO_0000029 RTN | [`return-to-database-or-resource/`](return-to-database-or-resource/) | Accepted terms, Compute environment |
| DUO_0000025 TS | [`time-limit-on-use/`](time-limit-on-use/) | Accepted terms, Compute environment |
| DUO_0000026 US | [`user-specific-restriction/`](user-specific-restriction/) | Platform account |

These end in Grant download. [`FL/`](FL/) holds the two cards for federated inference,
which end in Grant inference and read credentials about the script a requester brings.

## Writing a card

Draw it in the [Policy Composer](../docs/docs/composer.md) of the docs site: load a card or
start from the component library, wire each output to an input of the same credential
type, check it, and download its `graph.json`. A new card component goes in
`policy_components/` with its `component.rego`, unit tests and `component.json`.

## Tests

[`../policy_components/run_tests.sh`](../policy_components/run_tests.sh) runs every card's
vectors through the graph reference implementation of pdo-contracts (`pdo.rego.graph`),
after the components' own tests, and compares each card with its single Rego module on
`main`. [`../tools/policy_catalog/build_catalog.py`](../tools/policy_catalog/build_catalog.py)
checks the graphs, components, manifests and credential types against each other. CI runs
both.
