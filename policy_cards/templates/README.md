# Rule templates

Several DUO cards differ only in their presets: the rule is the same, and the card
fixes what the owner's form starts from. Such a rule lives here once, and each card
names it in its manifest (`"template": "<name>"`).

| Template | Rule | Cards |
|----------|------|-------|
| [`purpose-allowed/`](purpose-allowed/) | the requester's research has a purpose the owner allows | GSO, RS, POA |
| [`purpose-prohibited/`](purpose-prohibited/) | the requester's research has none of the purposes the owner prohibits | NMDS, NCU, NPOA |
| [`secure-results/`](secure-results/) | the requester accepted the required terms and handles results securely | MOR, RTN |

A template is a module like any other: `package subpolicy`, with its own tests. The
template registry gives each card the template's source as its rule, so a card and
its template are always the same code.
