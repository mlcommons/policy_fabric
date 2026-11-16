# End-to-End Tutorial: A Policy That Walks a Chain

This tutorial shows what a policy built from **policy components** can do. A dataset requires **ethics approval**, and nobody has written the requester an ethics approval of her own. What exists is a chain of credentials about four different subjects, each signed by the office that keeps it. The ethics approval card is a graph of small components that join that chain, link by link, into the decision.

A credential can also stand in for part of the chain. The IRB office can sign an **IRB clearance** directly, and the card's graph accepts a presented one in place of the components that would produce it. The requester's checklist says which way she can qualify.

If you have not done the [download tutorial](tutorial.md) yet, do that one first. This tutorial assumes its terms.

---

## The story

A research institution shares a dataset only with researchers whose work has ethics approval. A researcher, Rana, works in the team of a principal investigator (PI), Dr. Alice, whose project — a glucose study — was approved by an ethics committee for health research. Every link of the chain that implies Rana's approval exists:

```text
Rana ──member of the team of──► Dr. Alice ──owns──► the glucose study ──declares its use──► health research
  │                                                       │
affiliated with Best University                approved by committee 7, for health research
                                                          │
                              committee 7 is accredited for Best University
```

The card's graph joins it in three steps, each a policy component:

1. **ProjectMembership** — Rana is on the team of the PI who owns the glucose study, so the project is hers.
2. **InstitutionalIRBApproval** — committee 7 approved the project, and committee 7 is accredited for Best University.
3. **IRBClearance** — Rana belongs to that university, and the project approved is hers: she is cleared for the purposes the committee approved.

Then **EthicsApprovalRequired**, the card's own component, checks that every use the project declares is a purpose the committee approved, and **Grant download** releases the data to Rana's session key.

| Persona | Identity | What they do |
| --- | --- | --- |
| The offices | `vc_issuer` | Run three hand-signing authorities (a records office and an ethics registry that sign the chain, and the IRB office) and the `Session keys` system authority. In real life these are different organizations; here one identity runs them all. |
| Dataset Owner | `data_owner` | Exposes the dataset behind the ethics approval card, accepting the offices for each credential the graph reads. |
| Requester | `data_user` | Rana. Checks what she needs, and downloads the dataset. |

> **🔁 "Switch identity" callout** — Whenever you see this, use the **Identity dropdown at the top-right of the navbar** and pick the username.

The DIDs of Dr. Alice, the project, the committee and the university are plain example DIDs. They are only ever named inside credentials:

| Who | DID |
| --- | --- |
| Dr. Alice (the PI) | `did:example:pi_alice` |
| The glucose study (the project) | `did:example:glucose_study` |
| Committee 7 | `did:example:committee_7` |
| Best University | `did:example:best_university` |

---

## Part 1 — Requester: copy the wallet's DID

> **🔁 Switch identity to `data_user`.**

1. Go to **Wallets** → **Open** your wallet.
2. Under **Wallet Info**, click **Copy** next to the **DID**.

> 📋 **Keep this as `USER_DID` in your notes.**

---

## Part 2 — The offices set up their authorities

> **🔁 Switch identity to `vc_issuer`.**

1. Go to **Authorities** → **+ Create Authority**. **Name:** `University records office`. **Kind:** **Hand-signing**. **Credentials it signs:** **Team membership**, **Project ownership**, **Affiliation**. **What it checks:** `Keeps the university's teams, projects and appointments.` → **Create**.
2. **+ Create Authority**. **Name:** `Ethics registry`. **Kind:** **Hand-signing**. **Credentials it signs:** **IRB approval**, **Ethics committee accreditation**, **Intended data use**. **What it checks:** `Records committee approvals, accreditations and the uses projects declare.` → **Create**.
3. **+ Create Authority**. **Name:** `Best University IRB office`. **Kind:** **Hand-signing**. **Credentials it signs:** **IRB clearance**. **What it checks:** `Reviews each protocol before clearing it.` → **Create**.
4. **+ Create Authority**. **Name:** `Session keys`. **Kind:** **System**. → **Create**.

*What's happening:* an IRB clearance is a credential a component produces, and one an authority may also issue directly — its schema marks it *presentable*. That is why the IRB office can offer it. A credential only components produce, such as a download grant, is not offered for signing at all.

---

## Part 3 — Dataset Owner: one card, the whole chain

> **🔁 Switch identity to `data_owner`.**

1. **Assets** → **+ Register Asset**. **Name:** `study_data`. **Data Path:** `/tmp/asset_data.txt` → **Register Asset**.
2. **Open** `study_data`. In the **Expose** panel:
      - **Policies:** check **IRB · Ethics approval required**. Its graph is drawn under the list, from the credentials on the left to the capability on the right. None of its components has parameters.
      - **Accepted authorities**, one row per credential the graph reads:
          - **Team membership**, **Project ownership**, **Affiliation:** check `University records office`.
          - **IRB approval**, **Ethics committee accreditation**, **Intended data use:** check `Ethics registry`.
          - **IRB clearance:** check `Best University IRB office`.
          - **Project membership:** no authority in the directory issues it; leave it.
          - **Session key:** `Session keys` is already checked.
3. **Review** lists the ways a requester can meet the graph, the shortest first: *IRB clearance + Intended data use + Session key; or …* — down to the whole chain. One way ends *(no authority accepted for all)*: it needs a project membership, and you accepted no one for it. Click **Expose**.

*What's happening:* the policy is the card's graph, set on the asset's `rego_policy_agent` with `set_policy_graph`. The contract validates it against its components, and lists its **requirement alternatives**: every bundle of credentials that satisfies it. A presented IRB clearance from an authority you accept stands in for ProjectMembership, InstitutionalIRBApproval and IRBClearance together. A clearance from an authority you do not accept does not count, and then the components walk the chain instead.

---

## Part 4 — Requester: what am I missing?

> **🔁 Switch identity to `data_user`.**

1. **Assets** → **Use** on `study_data` → choose your wallet for the **User** role.
2. The checklist shows the shortest way to qualify:
      - **IRB clearance — Ask:** *Ask Best University IRB office.*
      - **Intended data use — Ask:** *Ask Ethics registry.*
      - **Session key — Automatic.**

**Request Download** stays disabled. Rana could ask the IRB office for a review. Instead, her PI's offices send her the chain.

---

## Part 5 — The offices deliver the chain to Rana's wallet

> **🔁 Switch identity to `vc_issuer`.**

Most credentials below are **about** someone else (Dr. Alice, the project, the committee) but **delivered to** Rana's wallet, as a copy she can present. Open the authority, click **Sign Credential**, and fill:

| Authority | Credential | About | Deliver to wallet | Claims |
| --- | --- | --- | --- | --- |
| University records office | Team membership | `USER_DID` | `USER_DID` | Member of team of: `did:example:pi_alice` |
| University records office | Project ownership | `did:example:pi_alice` | `USER_DID` | Owns: `did:example:glucose_study` |
| University records office | Affiliation | `USER_DID` | `USER_DID` | Is member of: `did:example:best_university`, Type of membership: `staff` |
| Ethics registry | IRB approval | `did:example:glucose_study` | `USER_DID` | Is approved by ethics committee: `did:example:committee_7`; Purposes: `HMB` |
| Ethics registry | Ethics committee accreditation | `did:example:committee_7` | `USER_DID` | Responsible for: `did:example:best_university` |
| Ethics registry | Intended data use | `did:example:glucose_study` | `USER_DID` | Use only for: Purposes `HMB`, Diseases `MONDO:0005015` |

---

## Part 6 — Requester: qualified by the chain

> **🔁 Switch identity to `data_user`.**

1. **Wallets** → open your wallet. **Stored Credentials** lists the six, each with whom it is about and who signed it.
2. **Assets** → **Use** on `study_data` → choose your wallet. The checklist now shows the whole chain, every credential **Held**, and **Session key — Automatic**: of the ways to meet the graph, this is the one Rana is ready for.
3. Click **Request Download**. The data appears:

   ```text
   The eagle lands at midnight.
   ```

*What's happening in the background:*

1. The app gets a session key from `Session keys`.
2. It presents Rana's wallet — her own credentials and the copies about Dr. Alice, the project and the committee — to the asset's policy agent, naming the session key.
3. The contract plans the graph: no IRB clearance was presented, so it runs the components that produce one. ProjectMembership finds Rana's project through Dr. Alice, InstitutionalIRBApproval finds the committee's accreditation for Best University, IRBClearance matches Rana's affiliation to it, and EthicsApprovalRequired checks the project's declared use against the approved purposes. Grant download grants to the holder of the session key.
4. Before signing anything, the contract verifies every credential the components read against the authorities the owner accepts for its type. It then issues the decision, and the guardian returns the data encrypted to Rana's session key.

Rana's wallet still holds no IRB clearance: the policy joined the chain itself.

---

## What you just built

```text
University records office ──signs──► Team · Project ownership · Affiliation       ─┐ copies in
Ethics registry           ──signs──► IRB approval · Accreditation · Intended use  ─┘ Rana's wallet
                                                    │ presented to
                                                    ▼
             study_data's policy: the ethics approval card, a graph of components
               ProjectMembership ─► IRBClearance ◄─ InstitutionalIRBApproval
                                        │   (or a presented IRB clearance, from
                                        │    Best University IRB office)
                                        ▼
                               EthicsApprovalRequired ─► Grant download
                                                    │
                                                    ▼
                                      capability ──► guardian ──► Rana
```

The owner decided **what** to require — ethics approval, as the card's graph says it — and **whom to believe** for each credential, as two separate choices. A registry that clears researchers directly would be one more authority to accept for IRB clearances, with no change to the graph at all.
