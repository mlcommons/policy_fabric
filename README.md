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

## Citation

```
@inproceedings{kassem2026decentralized,
  title = {Decentralized AI Governance Must Decouple Policy Processing from Capability Enforcement},
  author = {Kassem, Hasan and Anagnostopoulos, Christoforos and Aristizabal, Alejandro and Bakas, Spyridon and Banks, Orion GB and Benjelloun, Omar and Cai, Tian and Cansiz, Sergen and Chicco, Davide and Foley, Patrick and Hossain, Showkot and Jung, Taeho and Kairouz, Peter and Liu, Yanchen and Lorenzi, Marco and Mattson, Peter and Novakowski, Ann K and O’Connor, Michael and Roth, Holger R and Sannyasi, Adrish and Savvaidis, Charalampos and Sheller, Micah and Solooki, David and Stripelis, Dimitris and Umeton, Renato and Vesin, Marc and Wang, Ray and Zhang, Wenbin and Bowman, Mic and Karargyris, Alexandros},
  booktitle = {40th Annual Conference on Neural Information Processing Systems (NeurIPS), Position Paper Track},
  year = {2026},
}
```

## License

Copyright MLCommons. All rights reserved. Licensing to be determined. See [LICENSE](LICENSE).
