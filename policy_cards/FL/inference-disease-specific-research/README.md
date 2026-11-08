# FL-DS — Disease-Specific Research, for inference

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

**Rule:** The script declares a use within your disease scope.

The data stays put and a script runs against it, so this card asks what the code
is for rather than who is asking. The script asset holds an
`IntendedDataUseCredential` about itself, from an authority this site accepts,
and at least one of its `useOnlyFor.diseases` must be in the owner's
`allowedDiseases`.

Which script runs is fixed by the inference delivery module, which authorizes
the digest of the same script asset; both read facts about the one `Script`
holder.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| Script | `IntendedDataUseCredential` | the script | `useOnlyFor.diseases` |

**Parameters**

- `allowedDiseases` — MONDO codes of the diseases research may study.

Each fact must be about the holder of its role, and from an authority this asset
accepts for that type. The card names no operation: the delivery module of the
asset's guardian does.

> The executable rule is [`policy.rego`](policy.rego); this file is its
> human-readable companion, and [`card.json`](card.json) is its manifest.
