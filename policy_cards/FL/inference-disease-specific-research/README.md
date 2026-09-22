# FL-DS — Disease Specific Research (inference)

**Rule type:** Permission (constraint) · **Outcomes:** allow / deny

The inference counterpart of [DUO_0000007 DS](../../disease-specific-research/).
When the data never moves, the thing that must declare its purpose is the code that
will run against it, so both credentials this policy reads are about the script.

The script presents an **IntendedDataUseCredential** (claim `useOnlyFor.diseases`)
whose disease scope intersects the owner's allowed MONDO codes, and a
**ScriptHashCredential** (claim `scriptHash`) stating its content digest. Both must
name the **same script** as their subject — a declared use attached to one script
says nothing about another, and without that tie an in-scope declaration could be
paired with an unrelated digest.

Access is **allowed** when one script both declares an in-scope disease and states
its digest; otherwise it is **denied**.

**Requirements** (`data.subpolicy.requirements`):

```json
{
  "Script": ["IntendedDataUseCredential", "ScriptHashCredential"]
}
```

**Policy data:** `allowedDiseases: [..]`
**Context returned:** `{ "script_digest": "<approved script digest>" }`

> Source of truth for the executable logic is [`policy.rego`](policy.rego); this
> file is the human-readable companion. The two are maintained in parallel.
