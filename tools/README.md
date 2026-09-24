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
registering any asset behind an inference guardian. The guardian's FL client
announces itself to that server as soon as it comes up, and a site that
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
webapp ──lists──► FL server ──► its DID -> FL client mapping: the connected sites
                                (each client joined with the asset DID it holds)
   │ resolves each DID through the asset registry
   ▼
one capability per selected site, each from that site's own policy
   │ submitted together, each tagged with its asset DID
   ▼
FL server ──matches each DID to its client, addresses the job to it──►
                                                          FL client ──► guardian
                                           (digest + capability)   ◄── yes / no
```

The FL client holds the data, not the guardian. It hashes the script it was
sent and asks its guardian core, with the capability; the core compares that
digest against the one the capability authorizes and answers yes or no, and the
client runs the script over its data only on a yes.

The asset list has no Use button for these; it points at the Federated page
instead.
