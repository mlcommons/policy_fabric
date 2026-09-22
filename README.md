# Policy Fabric

An open reference implementation of **decoupled AI governance**: governance requirements are packaged as machine-readable *policy objects*, the evidence that satisfies them as *verifiable credentials*, so that policy processing is cleanly separated from capability enforcement.

📖 **[Full documentation](https://docs.mlcommons.org/policy_fabric/)** — concepts, architecture, and two hands-on tutorials.

## Try it

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/mlcommons/policy_fabric?ref=main)

The devcontainer brings up the policy engine, registries, and webapp; open the forwarded port **8000** and follow a tutorial:

- **[Download](https://docs.mlcommons.org/policy_fabric/tutorial/)** — data leaves, encrypted to a requester the policy checked. Start here.
- **[Inference](https://docs.mlcommons.org/policy_fabric/tutorial_inference/)** — data stays put and approved code comes to it, at two hospitals at once.

## Layout

```
policy_cards/   Policy Card instances (Rego + docs)
credentials/    Credential type definitions (the evidence vocabulary)
tools/          Webapp, registries, guardians, FL server, policy engine
docs/           The documentation site
```

## Disclaimer

This is a reference implementation, not a production governance system. It ships without warranty and is not legal or compliance advice.

## License

Copyright MLCommons. All rights reserved. Licensing to be determined. See [LICENSE](LICENSE).
