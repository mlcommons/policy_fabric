# Download delivery

**Rule:** Release the data encrypted to the requester's session key.

The delivery module of a download guardian. The webapp adds it to every policy agent
in front of a download guardian; the owner never picks it. It describes the
`policy_decision` about the requester, whose claims name the operation the guardian
runs -- `do_download` -- and its one parameter, the channel key the data is
encrypted to.

| Role | Fact | About | Read from it |
|------|------|-------|--------------|
| User | `publicKeyCredential` | the requester | `key` |

The key must be bound to the requester (`subject == holders.User`) by an authority
the owner accepts for session keys. The requester may hold several; the webapp names
the one whose private half it holds in `request.channel_key`.

> The executable rule is [`policy.rego`](policy.rego); [`card.json`](card.json) is
> its manifest.
