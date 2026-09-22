# inference guardian

A guardian for assets that are never handed out: the code comes to the data. It
ships two pieces that run together on the data holder's host.

## `guardian_core`

A PDO guardian service whose one capability handler is `do_inference`. Same
shape as the download guardian's `do_download`, with one addition: the
capability's parameters carry a `script_digest` alongside the `channel_key`, and
the caller must separately report the digest it computed over the script it
actually holds.

```
capability parameters   { "script_digest": "sha256:...", "channel_key": "..." }   authenticated
request context         { "calculated_script_digest": "sha256:..." }              from the caller
```

The core releases the data only when the two digests agree. That comparison is
the whole point of the design: credentials about a blessed script prove nothing
about the code that runs unless something re-measures the code at the moment the
data is released.

The request context reaches the operation through the `request_context` field on
`process_capability`, which every capability request carries — an operation with
nothing to check against it simply ignores it.

Only the digest is required. The channel key is carried when a policy produces
one, but is not yet used — the data goes back over loopback, in the clear. A
policy that governs the code alone (FL-DS) says nothing about the requester and
so has no channel key to carry; requiring one here would make such a policy
unsatisfiable for a reason unrelated to what it decides.

## `fl_framework`

A mock FL client. It polls an FL server (it never listens), and each job carries
a script and a capability package. For each job it hashes the script, redeems the
capability at the core over `localhost`, prints what it would run, and reports
fixed metrics back to the server.

It claims jobs under the name given by `--fl-client-id`, and a submitter addresses
a job to that name. A capability is minted for one guardian and is refused at any
other, so once a host runs two of these — two datasets, two policies — "the oldest
pending job" stops being a safe answer to what a client should run.

It depends on nothing from PDO, which is the point: a real FL framework would not
be a PDO component either. All it has to know is how to POST a capability package
to a guardian.

## Running

Both pieces come up together, `start_services.sh` bringing up the storage
service, the core, and then the client:

```bash
./build.sh --client-image mlcommons/pdo_base_client:v2 \
           --image mlcommons/toy_inference_guardian:v2

./run.sh --image mlcommons/toy_inference_guardian:v2 \
         --interface 127.0.0.1 --port 7900 --sservice-port 7901 \
         --guardian-host localhost \
         --data-path /tmp/asset_data.txt \
         --fl-server-url http://host.docker.internal:7920 \
         --fl-client-id localhost:7900
```

The container is named after its port, so a second guardian on another port runs
alongside the first rather than replacing it.

The core must reach the machine the policy author binds the token from, and the
client must reach the core over loopback, so this guardian is expected to run on
the policy author's own host.
