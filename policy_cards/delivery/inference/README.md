# Inference delivery

**Rule:** Run the approved script, identified by its digest.

The delivery module of an inference guardian. The webapp adds it to every policy
agent in front of an inference guardian; the owner never picks it. It describes the
`policy_decision` about the script, whose claims name the operation the guardian
runs -- `do_inference` -- and its one parameter, the digest of the script that may
run. The FL client measures the script it receives and the
guardian runs it only if the two digests match.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| Script | `ScriptHashCredential` | the script | `scriptHash` |

The webapp names the digest of the script it actually sends in
`request.script_digest`, so the capability is minted for that exact code.

> The executable rule is [`policy.rego`](policy.rego); [`card.json`](card.json) is
> its manifest.
