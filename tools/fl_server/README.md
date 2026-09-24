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

## The DID -> FL client mapping

An FL client sits in front of exactly one dataset, and that dataset is an asset
with a DID. The client joins under its own ID (`client_id`) and reports that DID
with it, when it joins and on every poll. The server keeps the pair in memory —
one client per DID, one DID per client — and that mapping is what makes two
things possible:

| Question | Answered by |
| --- | --- |
| which sites are available to run against? | `GET /clients` — the mapping itself, one entry per DID; the Federated page resolves each DID through the asset registry |
| which capability in a round belongs to which client? | the mapping again, at `POST /rounds`: each participant's DID is matched to the client holding it, and its job is addressed to that `client_id`. Only that client can claim it |

The second is not a convenience. A capability is minted for one guardian and is
refused at every other, so an unlabelled pile of them could only be handed out by
guessing — and every wrong guess is a site failing on a capability its guardian
was always going to refuse.

What the mapping does not have an entry for is said at once rather than waited
on:

- a round participant whose DID no connected client holds is recorded `failed`
  when the round is submitted, with that reason;
- a client that stops holding a DID — it now announces another (a guardian
  redeployed onto its port), or it went quiet and another client took the DID
  over — has its unclaimed jobs for that DID failed, since no one else may claim
  them.

A client is connected while it keeps polling, and counts as gone 30 seconds
after its last poll.

Announcing is not authenticated and is not meant to be. This is a job board;
what actually decides whether a job may run over an asset's data is the
capability, which that asset's own guardian checks when the FL client holding
the data asks it. A second client claiming a DID that a connected client holds is
refused with a `409`; once the holder has gone quiet, whoever claims the DID next
gets its future jobs — and capabilities only the asset's own guardian will accept.

## API

| Method | Path                 | Body / query                          | Returns                        |
|--------|----------------------|---------------------------------------|--------------------------------|
| GET    | `/info`              |                                       | `{service, clients, rounds, jobs}` |
| POST   | `/clients`           | `{client_id, asset_did, ...}`         | `{ok, client}`; `409` if another connected client holds that DID |
| GET    | `/clients`           |                                       | `{clients: [...]}`, one per DID, with `online` |
| POST   | `/rounds`            | `{script, participants: [{asset_did, capability}]}` | the round, each site with the `client_id` it was matched to |
| GET    | `/rounds/<id>`       |                                       | per-site `client_id`, status + `aggregate` |
| GET    | `/jobs/next`         | `?client_id=&asset_did=`              | `{job}` addressed to that client, or `{job: null}`; `409` as for `POST /clients` |
| POST   | `/jobs/<id>/metrics` | `{metrics}` or `{error}`              | `{job_id, status}`             |
| GET    | `/jobs/<id>`         |                                       | the job record, without script |

A status poll never returns the script or the capability: those are the client's
to see, not the submitter's to re-read.

## Rounds

`POST /rounds` fans one script out into one job per participant, each addressed
to the client the mapping names for its DID. The submitter names assets, never
clients. A round is *complete* once every site has answered and at least one of
them ran it; a site that fails is a fact about that site, not a broken round. `aggregate` is the
sample-weighted mean of what the sites reported — the only part of this that is
recognisably an aggregator, and the only place the sites' numbers meet.

The submitter is the webapp's federated flow
(`pdo_client/webapp/app/views/federated.py`); the consumer is the FL client that
runs beside each inference guardian and holds its data
(`tools/guardians/inference/fl_framework/`).
