# fl server

A toy federated-learning server: the aggregator a requester submits a **round**
to, and the FL clients beside each guardian poll.

It knows nothing about PDO. A round is a script plus one opaque capability
package per site; a result is whatever metrics each site reports. Everything
lives in memory, and nothing is retried or expired.

```bash
./run.sh --image mlcommons/pdo_fl_server:v2 --interface 0.0.0.0 --port 7920
```

It is containerized and long-lived, and it is **not** started by the webapp: a
round goes to a server that is already there, named by whoever asks for the
round. `../start_fl_server.sh` brings one up.

## Clients announce the asset they hold

An FL client sits in front of exactly one dataset, and that dataset is an asset
with a DID. The client reports that DID when it joins and on every poll, which is
what makes two things possible:

| Question | Answered by |
| --- | --- |
| which sites are available to run against? | `GET /clients` — the list the Federated page joins against the asset registry, on the DID |
| which capability in a round belongs to which client? | the DID a job is addressed to, matched against the DID the claiming client announced |

The second is not a convenience. A capability is minted for one guardian and is
refused at every other, so an unlabelled pile of them could only be handed out by
guessing — and every wrong guess is a site failing on a capability it was never
able to redeem.

Announcing is not authenticated and is not meant to be. This is a job board;
what actually decides whether a client may have an asset's data is the
capability, which that asset's own guardian checks. Claiming someone else's DID
here gets you their job and a capability you cannot redeem.

## API

| Method | Path                 | Body / query                          | Returns                        |
|--------|----------------------|---------------------------------------|--------------------------------|
| GET    | `/info`              |                                       | `{service, clients, rounds, jobs}` |
| POST   | `/clients`           | `{client_id, asset_did, ...}`         | `{ok, client}`                 |
| GET    | `/clients`           |                                       | `{clients: [...]}` with `online` |
| POST   | `/rounds`            | `{script, participants: [{asset_did, capability}]}` | the round   |
| GET    | `/rounds/<id>`       |                                       | per-site status + `aggregate`  |
| GET    | `/jobs/next`         | `?client_id=&asset_did=`              | `{job}` or `{job: null}`       |
| POST   | `/jobs/<id>/metrics` | `{metrics}` or `{error}`              | `{job_id, status}`             |
| GET    | `/jobs/<id>`         |                                       | the job record, without script |

A status poll never returns the script or the capability: those are the client's
to see, not the submitter's to re-read.

## Rounds

`POST /rounds` fans one script out into one job per participant. A round is
*complete* once every site has answered and at least one of them ran it; a site
that fails is a fact about that site, not a broken round. `aggregate` is the
sample-weighted mean of what the sites reported — the only part of this that is
recognisably an aggregator, and the only place the sites' numbers meet.

The submitter is the webapp's federated flow
(`pdo_client/webapp/app/views/federated.py`); the consumer is the FL client
bundled with the inference guardian (`tools/guardians/inference/fl_framework/`).
