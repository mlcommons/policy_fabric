# End-to-End Tutorial: One Fact, Two Authorities

This tutorial shows what separating policies from evidence buys. A dataset requires **ethics approval**, and that is the whole policy: one fact. Who may establish that fact is a separate decision, and the owner makes it by accepting two authorities that work in completely different ways:

- **Best University IRB office**, a *hand-signing* authority: a person reviews the protocol and signs an ethics approval.
- **Accredited-committee check**, a *rule-based* authority: a locked rule issues an ethics approval when the requester's project is approved by an ethics committee accredited for their PI's institution.

The requester's checklist says which way they can qualify, and the policy never knows which one they took.

If you have not done the [download tutorial](tutorial.md) yet, do that one first. This tutorial assumes its terms.

---

## The story

A research institution shares a dataset only with researchers whose work has ethics approval. A researcher, Rana, works in the team of a principal investigator (PI), Dr. Alice, whose project — a glucose study — was approved by the university's ethics committee. Nobody has written Rana an ethics approval of her own, but every link of the chain that implies one exists:

```text
Rana ──member of the team of──► Dr. Alice ──owns──► the glucose study
                                   │                      │
                       affiliated with Best University    approved by committee 7
                                                          │
                              committee 7 is accredited for Best University
```

Before authorities, the dataset's policy had to walk this chain itself: seven credentials about four subjects, for a one-line rule. Here, the chain is the **Accredited-committee check's** business. The policy reads one fact about Rana.

| Persona | Identity | What they do |
| --- | --- | --- |
| The offices | `vc_issuer` | Run four authorities: a records office and an ethics registry that sign the chain, the accredited-committee check, and the IRB office. In real life these are different organizations; here one identity runs them all. |
| Dataset Owner | `data_owner` | Exposes the dataset behind the ethics approval card, accepting both ways to establish the fact. |
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

### 2.1 Two offices that sign the chain

1. Go to **Authorities** → **+ Create Authority**.
2. **Name:** `University records office`. **Kind:** **Hand-signing**. **Facts it attests:** **Team membership**, **Project ownership**, **Affiliation**. **What it checks:** `Keeps the university's teams, projects and appointments.` → **Create**.
3. **+ Create Authority** again. **Name:** `Ethics registry`. **Kind:** **Hand-signing**. **Facts it attests:** **IRB approval**, **Ethics committee accreditation**. **What it checks:** `Records committee approvals and accreditations.` → **Create**.

### 2.2 The accredited-committee check

1. **+ Create Authority**. **Name:** `Accredited-committee check`. **Kind:** **Rule-based**.
2. Under **Authority card**, choose **Accredited-committee check**. (Use **View** to read the card and its rule.) → **Create**.
3. Open it. The page shows its **Rule**, which is locked: accepting this authority means accepting exactly this rule.
4. Under **Accepted authorities for its inputs**, accept, row by row:
      - **Team membership**, **Project ownership**, **Affiliation** → `University records office · Hand-signing` → **Accept**
      - **IRB approval**, **Ethics committee accreditation** → `Ethics registry · Hand-signing` → **Accept**

*What's happening in the background:* the authority is a `rego_policy_agent` contract, the same contract that holds an asset's policy. Its policy is an authority card — the same shape as a policy card, except that the credential its result describes is a fact instead of a policy decision. The rule declares the type it issues (`EthicsApprovalCredential`), and the contract reads it once, when the rule is set, so the rule can only ever issue ethics approvals. Its inputs count only when signed by an authority its operator accepted, exactly as a policy's facts do.

### 2.3 The IRB office, and session keys

1. **+ Create Authority**. **Name:** `Best University IRB office`. **Kind:** **Hand-signing**. **Facts it attests:** **Ethics approval**. **What it checks:** `Reviews each protocol before approving it.` → **Create**.
2. **+ Create Authority**. **Name:** `Session keys`. **Kind:** **System**. → **Create**.

---

## Part 3 — Dataset Owner: one policy, two ways to meet it

> **🔁 Switch identity to `data_owner`.**

1. **Assets** → **+ Register Asset**. **Name:** `study_data`. **Data Path:** `/tmp/asset_data.txt` → **Register Asset**.
2. **Open** `study_data`. In the **Expose** panel:
      - **Policies:** check **IRB · Ethics approval required**. It has no parameters.
      - **Accepted authorities → Ethics approval:** check **both** `Best University IRB office` and `Accredited-committee check`. The rule-based option shows whom it accepts for its inputs.
      - **Session key:** `Session keys` is already checked.
3. **Review** reads: *Requesters will need: Ethics approval (Best University IRB office or Accredited-committee check), Session key (automatic).* Click **Expose**.

*What's happening:* the policy is the ethics approval card — one fact, about the requester — and the download delivery module. It reads the approval as a fact about whoever presents it, so a hand-signed approval and one the rule issued are the same thing to it.

---

## Part 4 — Requester: what am I missing?

> **🔁 Switch identity to `data_user`.**

1. **Assets** → **Use** on `study_data` → choose your wallet for the **User** role.
2. The checklist shows:
      - **Ethics approval — Ask:** *Ask Best University IRB office.* Rana holds nothing the accredited-committee check could read, so the only way left is to ask the office that signs by hand.
      - **Session key — Automatic.**
3. An ethics approval is about a project, so the modal also asks for the **Project** this download is for — and says none of her wallets names one yet.

**Request Download** stays disabled. Rana could ask the IRB office for a review. Instead, her PI's offices send her the chain.

---

## Part 5 — The offices deliver the chain to Rana's wallet

> **🔁 Switch identity to `vc_issuer`.**

Each credential below is **about** someone else (Dr. Alice, the project, the committee) but **delivered to** Rana's wallet, as a copy she can present. Open the authority, click **Sign Credential**, and fill:

| Authority | Fact | About | Deliver to wallet | Claims |
| --- | --- | --- | --- | --- |
| University records office | Team membership | `USER_DID` | `USER_DID` | Member of team of: `did:example:pi_alice` |
| University records office | Project ownership | `did:example:pi_alice` | `USER_DID` | Owns: `did:example:glucose_study` |
| University records office | Affiliation | `did:example:pi_alice` | `USER_DID` | Is member of: `did:example:best_university`, Type of membership: `faculty` |
| Ethics registry | IRB approval | `did:example:glucose_study` | `USER_DID` | Is approved by ethics committee: `did:example:committee_7` |
| Ethics registry | Ethics committee accreditation | `did:example:committee_7` | `USER_DID` | Responsible for: `did:example:best_university` |

---

## Part 6 — Requester: qualified by the rule

> **🔁 Switch identity to `data_user`.**

1. **Wallets** → open your wallet. **Stored Credentials** lists the five, each with whom it is about and who signed it.
2. **Assets** → **Use** on `study_data` → choose your wallet. The checklist now shows:
      - **Ethics approval — Automatic:** *Obtained on the way, from Accredited-committee check.*
      - **Session key — Automatic.**
3. **Project:** choose `did:example:glucose_study` — the copy of Dr. Alice's project ownership in your wallet names it.
4. Click **Request Download**. The data appears:

   ```text
   The eagle lands at midnight.
   ```

*What's happening in the background:*

1. The app presents Rana's wallet to the **Accredited-committee check**, with the project she named. Its contract checks each input was signed by an authority its operator accepted, and runs the rule: Rana is in Dr. Alice's team, Dr. Alice owns the glucose study, committee 7 approved it, and committee 7 is accredited for Dr. Alice's university. It issues Rana an **ethics approval** for the glucose study, which lands in her wallet.
2. The app gets a session key from `Session keys`.
3. The dataset's policy reads one fact: an ethics approval about Rana, from an authority the owner accepts. It allows, the delivery module describes the decision naming Rana's session key, and the guardian returns the data encrypted to it.

Back on the wallet page, the new **Ethics approval** credential shows `Accredited-committee check` as its signer.

---

## What you just built

```text
University records office ──signs──► Team · Project ownership · Affiliation ─┐ copies in
Ethics registry           ──signs──► IRB approval · Committee accreditation ─┘ Rana's wallet
                                                    │ presented to
                                                    ▼
                               Accredited-committee check  (locked rule, accepts both offices)
                                                    │ issues
                                                    ▼
Best University IRB office ─(or)─► Ethics approval about Rana
                                                    │
                                                    ▼
                         study_data's policy: "the requester has ethics approval"
                                                    │ accepts both authorities
                                                    ▼
                                      capability ──► guardian ──► Rana
```

The owner decided **what** to require — ethics approval — and **whom to believe** about it, as two separate choices. The chain of team, project, committee and accreditation never reached the policy, and a new way to establish the fact — a national ethics registry, say — would be one more authority to accept, with no change to the policy at all.
