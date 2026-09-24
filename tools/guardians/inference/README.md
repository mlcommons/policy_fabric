# inference guardian

A guardian for assets that are never handed out: the code comes to the data. It
ships two pieces that run together on the data holder's host, and **only one of
them has the data**.

| Piece | Holds the data? | Does |
| --- | --- | --- |
| `fl_framework` — the FL client | **yes**, mounted into its container | polls the FL server, asks the core before each job, runs it |
| `guardian_core` — the guardian | no | answers one question: may this script run? |

## `guardian_core`

A PDO guardian service whose one capability handler is `do_inference`. It has no
dataset. What it gets, per job, is the capability package and the digest the FL
client computed over the script it actually holds:

```
capability parameters   { "script_digest": "sha256:...", "channel_key": "..." }   authenticated
request context         { "calculated_script_digest": "sha256:..." }              from the caller
```

and what it returns is a yes or a no:

```
yes   HTTP 200   { "allowed": true, "script_digest": "sha256:...", "method_name": "do_inference" }
no    HTTP 422   operation failed
```

The answer is yes only when the two digests agree. That comparison is the whole
point of the design: credentials about a blessed script prove nothing about the
code that runs unless something re-measures the code at the moment it is about to
run.

A digest mismatch is the framework's failed-operation response, `422 operation
failed`. A capability that does not decrypt or does not validate (minted for a
different guardian, say) fails the request the way it does at every guardian; the
client treats anything other than a `200` with `"allowed": true` as a no.

This is the same answer `tools/dev/mock_inference_guardian` gives (the mock adds
`"mock": true`), so anything built against the mock works against this.

The request context reaches the operation through the `request_context` field on
`process_capability`, which every capability request carries — an operation with
nothing to check against it simply ignores it.

Only the digest is required. The channel key is carried when a policy produces
one, but is not used: nothing leaves this guardian but the answer. A policy that
governs the code alone (FL-DS) says nothing about the requester and so has no
channel key to carry; requiring one here would make such a policy unsatisfiable
for a reason unrelated to what it decides.

## `fl_framework`

A mock FL client, and the process the dataset is mounted into. It polls an FL
server (it never listens), and each job carries a script and a capability
package. For each job it:

1. hashes the script;
2. sends the digest and the capability to the core over `localhost`;
3. on a yes, reads its data, prints what it would run, and reports fixed metrics
   back to the server — on anything else it reports the job failed, without ever
   opening the data.

It claims jobs for the asset DID it announces (`--asset-did`), under the name
given by `--fl-client-id`. A capability is minted for one guardian and is refused
at any other, so once a host runs two of these — two datasets, two policies — "the
oldest pending job" stops being a safe answer to what a client should run.

It depends on nothing from PDO, which is the point: a real FL framework would not
be a PDO component either. All it has to know is how to POST a capability package
to a guardian and read back a yes or a no.

The guardian's answer is only as binding as the FL client that asks for it. The
client belongs to the data holder and runs in their environment, so that is the
trust assumption: the data holder's own FL framework asks its guardian, and obeys.

## Running

`run.sh` starts two containers from the same image and takes them down together:

| Container | Entry point | Data mount | Network |
| --- | --- | --- | --- |
| `pdo-inference-guardian-<port>` | `start_services.sh` — storage service + core | none | publishes `<port>` and `<sservice-port>` |
| `pdo-inference-guardian-<port>-fl-client` | `start_fl_client.sh` | `--data-path`, read-only | joins the core's network namespace, so the core is `localhost:7900` |

```bash
./build.sh --client-image mlcommons/pdo_base_client:v2 \
           --image mlcommons/toy_inference_guardian:v2

./run.sh --image mlcommons/toy_inference_guardian:v2 \
         --interface 127.0.0.1 --port 7900 --sservice-port 7901 \
         --guardian-host localhost \
         --data-path /tmp/asset_data.txt \
         --fl-server-url http://host.docker.internal:7920 \
         --fl-client-id localhost:7900 \
         --asset-did did:pdo:...
```

The containers are named after the port, so a second guardian on another port
runs alongside the first rather than replacing it.

The core must reach the machine the policy author binds the token from, and the
client must reach the core, so this guardian is expected to run on the data
holder's own host.
