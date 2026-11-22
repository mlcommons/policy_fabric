# Policy cards

A policy card states what must be true to use an asset. Each card is a **graph of
[policy components](../policy_components/)** (`graph.json`): small Rego components that
pass credentials and decisions to each other. Shared components join credentials into new
ones -- ProjectMembership turns a requester's team and their PI's project ownership into a
ProjectMembershipCredential -- and a card component checks the result against the owner's
parameters and decides. AllowIfAll joins the card's decision with the one that admits the
operation's parameter (ChannelKey's, the requester's session key; or ScriptDigest's, the
script's digest), and the graph's capability makes that decision into the operation the
asset's guardian redeems, `do_download` or `do_inference`.

| Decision | Made by | Lives in |
|----------|---------|----------|
| What must be true to use my data | the data owner | the cards' graphs, and each node's parameters |
| Whose word I accept, per credential type | the data owner | the trusted issuers of the asset's policy agent |
| How a credential is established | an authority's operator | an authority, on the webapp's Authorities page |
| What is unlocked, and how | the platform, per guardian type | the operation of the graph's capability, and its parameters |

A data owner selects one or more cards when exposing an asset. Their graphs compose into
one whose AllowIfAll takes every card's decision, sharing the components they have in
common, and the webapp sets
it on the asset's `rego_policy_agent` with `set_rego_policy`. The contract validates the
graph against its components' interfaces, plans per request which components run, runs
them, and issues the capability only after verifying every credential they read.

A decision is `{allow, parameters}`: whether it allows, and for each parameter it names the
values it admits, `subject` (whom it is about) among them. AllowIfAll allows when every
decision it takes allows and they admit a value in common for each parameter; its parameters
are those common values. The capability takes one decision, and issues the operation when
it allows, about exactly one subject, and admits the parameter the request names.

A credential a component produces can also be presented, when the card's graph accepts it
presented and an authority the owner accepts issued it: ProjectMembershipCredential and
IRBClearanceCredential (their schemas say `x-presentable`). A graph therefore lists every
bundle of credentials that satisfies it, its requirement alternatives, and a requester
presents one.

## Folders

Every card folder holds its `graph.json`, the `graph_tests.json` that states the
decisions the graph must reach, a `card.json` with its code, name and one-line rule, and
`policy_card.md`, the full Policy Card, which the webapp shows owners.

A card's `graph.json` is a template, so every node's `policy_data` is `{}` and every
`trusted_issuers` list is `[]`: the owner picks both when exposing an asset. The webapp
writes the owner's values into the asset's graph, and the contract stores each node's
`policy_data` apart from the graph, which it keeps with every `policy_data` empty.

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

These issue `do_download`. [`FL/`](FL/) holds the two cards for federated inference,
which issue `do_inference` and read credentials about the script a requester brings.

## Writing a card

1. **Its card component.** A card's own rule is a card component; write it first, as
   [`../policy_components/README.md`](../policy_components/README.md#writing-a-component)
   says, with `card` naming the folder you are about to create.
2. **`graph.json`.** Draw it in the [Policy Composer](../docs/docs/composer.md) of the docs
   site (to run it locally, see [`../docs/README.md`](../docs/README.md)): load a card or start
   from the component library, wire each output to an input of the same type, turn on accept
   presented where a registry may issue the joined credential, wire the card component's
   decision and ChannelKey's (or ScriptDigest's) into AllowIfAll and AllowIfAll into the
   capability, choose the operation, check it, and download it. Save it as `<folder>/graph.json`, or `FL/<folder>/graph.json` for an inference
   card. The committed graph lists `[]` for every type in `trusted_issuers` and leaves every
   node's `policy_data` empty: the owner chooses both when exposing an asset.
3. **`card.json`**: exactly `code` (the DUO abbreviation), `name` and `rule`, the one-line
   rule shown to the owner; `build_catalog.py` checks the keys.
4. **`graph_tests.json`**: the decisions the graph must reach. Start from a card's: every
   credential type the graph reads is a key of `registry`, every node has its `policy_data`,
   and there is an allow for each requirement alternative and a deny for each thing a
   component checks. The format is in
   [`../policy_components/tests/graph_tests.py`](../policy_components/tests/graph_tests.py), and the
   denial reasons in pdo-contracts' `rego-contract/docs/policy_graph.md`.
5. **`policy_card.md`**, the full Policy Card, written by hand from an existing card: its
   rule, the graph's components, the presented credentials and the parameters. The tests find
   cards by their `policy_card.md`. Add the card to the table above.
6. **Check it**, with `python3 tools/policy_catalog/build_catalog.py --repo . --out /tmp/catalog.json`
   and `policy_components/run_tests.sh` (see below).
7. **Serve it.** The template registry seeds from this folder each time it starts
   (`tools/docker_start_registries.sh` mounts it), so restarting the registry offers the card
   on the webapp's Expose form and Policies page. A change to `tools/policy_catalog/` needs the
   registry image rebuilt, since the image copies it.

## Tests

[`../policy_components/run_tests.sh`](../policy_components/run_tests.sh) runs every card's
graph tests through `policy_components/tests/policy_graph.py`, which runs the contract's own
validator and planner from a pdo-contracts checkout, after the components' own tests, and
compares each card that existed at commit `760742d`
with its Rego file there, from before cards became graphs.
[`../tools/policy_catalog/build_catalog.py`](../tools/policy_catalog/build_catalog.py)
checks the graphs, components, manifests and credential types against each other. CI runs
both.
