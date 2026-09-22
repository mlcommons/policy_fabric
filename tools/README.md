# Policy Fabric

## Components

| Folder                | What it is                                                            |
|-----------------------|-----------------------------------------------------------------------|
| `pdo_client/`         | the webapp and the PDO client it drives                               |
| `asset_registry/`     | toy asset registry                                                    |
| `template_registry/`  | toy policy card and credential schema registry                        |
| `policy_engine/`      | ledger and PDO services                                               |
| `guardians/`          | the guardians an asset can be put behind; see its own README          |
| `fl_server/`          | toy FL server the webapp submits federated rounds to                  |
| `tests/`              | the tutorials, driven through a browser; see its own README           |

## Setup

Build the policy_engine, guardians, the FL server and pdo_contract_base —
`docker_build_all.sh` does all of it, and names the pdo-contracts revision and
the image tag in one place at the top.

## Test

1. Run the ledger
2. Run the pdo services
3. Start a data guardian
4. generate user keys
5. Start the policies client

For the inference flow, also start the FL server (`start_fl_server.sh`) **before**
registering any asset behind an inference guardian. The guardian's bundled FL
client announces itself to that server as soon as it comes up, and a site that
never announced is a site no round can be addressed to.

`make_tutorial_files.sh` writes the files both tutorials register as assets, and
prints the script digest the inference tutorial asks for.

`tests/run_webui_inference_test.sh` does the whole of the above and then drives
the inference tutorial through a browser, recording it.

## How an inference asset is used

Not one at a time. An asset behind an inference guardian is one **site** of a
federated round, and the webapp's Federated page is where a requester picks the
sites and runs one script across all of them:

```
webapp ──lists──► FL server ──► the sites whose FL clients are connected
                                (each announced the asset DID it holds)
   │ joins them against the asset registry, on the DID
   ▼
one capability per selected site, each from that site's own policy
   │ submitted together, each tagged with its asset DID
   ▼
FL server ──hands each client the capability for the DID it announced──►
                                                          FL client ──► guardian
```

The asset list has no Use button for these; it points at the Federated page
instead.
