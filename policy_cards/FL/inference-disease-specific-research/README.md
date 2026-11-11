# FL-DS — Disease-Specific Research, for inference

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The script declares a use within your disease scope.

It reads IntendedDataUseCredential and ScriptHashCredential, compares them with its policy data, and outputs the InferenceGrantCredential that Grant inference takes.

The card is a graph of policy components. Each takes credentials, from the requester's presentation or
from the components before it, and outputs a credential of its own; the last, Grant inference, issues
`do_inference` for the digest of the script the request names.

| Policy Component | What it checks |
|---|---|
| DiseaseSpecificResearchForInference | It reads IntendedDataUseCredential and ScriptHashCredential, compares them with its policy data, and outputs the InferenceGrantCredential that Grant inference takes. |
| Grant inference | The end of every federated learning card. Issues do_inference for the script digest the request names, when every card on the asset granted that script, with that digest. |

**Presented credentials**, each from an authority the asset's owner accepts for its type:

| Role | Credential | About | Claims read |
|---|---|---|---|
| Script | Intended data use (`IntendedDataUseCredential`) | the script | `useOnlyFor.diseases` |
| Script | Script digest (`ScriptHashCredential`) | the script | `scriptHash` |

**Parameters:**

- **DiseaseSpecificResearchForInference · `allowedDiseases`** (array of strings): Allowed MONDO disease codes. An IntendedDataUseCredential qualifies if any entry of claims.useOnlyFor.diseases is in this list.

> The card is [`graph.json`](graph.json), decided as [`graph_vectors.json`](graph_vectors.json) says; its
> components are in [`policy_components/`](../../../policy_components/), and [`card.json`](card.json) names it.
