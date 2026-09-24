"""A mock federated-learning server.

This is the aggregator side of the FL story and knows nothing about PDO: to it, a
round is a script plus one opaque capability package per participating site, and a
result is whatever metrics each site reports back. It exists so the inference flow
has a realistic shape -- a requester hands one piece of work to an FL server and
every data holder's FL client pulls its own share of it down -- without a real FL
framework in the way.

**It keeps a DID -> FL client mapping.** An FL client sits beside one guardian,
in front of one dataset, and that dataset is an asset with a DID. The client
joins under its own ID and reports that DID, when it joins and on every poll, and
this server keeps the pair in memory: which client holds which asset, one each
way. The mapping answers the two questions the server exists to answer:

* *who is connected?* -- the list a requester picks participants from. A
  requester knows assets by DID, not FL clients by name; the mapping is what
  turns one into the other.
* *whose capability is whose?* -- a capability is minted for one guardian and is
  worth nothing at any other. A round names each participant by the DID its
  capability was minted for, and the server matches each one to the client
  holding that DID *when the round is submitted*: the job is addressed to that
  client, and no other client can claim it. A DID no connected client holds is
  reported failed at once, rather than queued for nobody.

A **round** is the unit a requester submits: one script, and a list of
``{asset_did, capability}`` participants. The server fans it out into one job per
participant, addressed to the client holding its DID, and aggregates the metrics
that come back.

| Method | Path                    | Body / query                          | Returns                       |
|--------|-------------------------|---------------------------------------|-------------------------------|
| GET    | `/info`                 |                                       | `{service, clients, ...}`     |
| POST   | `/clients`              | `{client_id, asset_did, ...}`         | `{ok, client}`; 409 if another connected client holds that DID |
| GET    | `/clients`              |                                       | `{clients: [...]}`, one per DID |
| POST   | `/rounds`               | `{script, participants:[{asset_did,capability}]}` | the round, each site matched to a `client_id` |
| GET    | `/rounds/<id>`          |                                       | the round, with aggregate     |
| GET    | `/jobs/next`            | `?client_id=&asset_did=`              | `{job}` or `{job: null}`; 409 as for `POST /clients` |
| POST   | `/jobs/<id>/metrics`    | `{metrics}` or `{error}`              | `{job_id, status}`            |
| GET    | `/jobs/<id>`            |                                       | the job record, without script|
"""

import argparse
import json
import logging
import threading
import time
import uuid
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

SERVICE_NAME = "fl_server"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"

TERMINAL_STATUSES = (STATUS_COMPLETE, STATUS_FAILED)

# How long after its last poll a client is still considered connected. A client
# polls every few seconds, so this tolerates a couple of missed polls without
# calling a live site dead.
CLIENT_TTL_SECONDS = 30


class DidHeldElsewhere(Exception):
    """A client claimed an asset that another connected client holds."""


class ClientRegistry:
    """The DID -> FL client mapping: which connected client holds which asset.

    A client is known by the ID it claims (``client_id``) and holds exactly one
    asset (``asset_did``); an asset is held by exactly one client. The second
    half is what makes the mapping usable for routing -- a DID resolves to one
    client or to none -- so a client claiming a DID that another *connected*
    client holds is refused. Once the holder has gone quiet the DID is free
    again, and whoever claims it next takes it over.

    Registration is not authenticated and is not meant to be: this server is a
    job board, and the thing that actually decides whether a job may run over an
    asset's data is the capability, which that asset's guardian checks. Claiming
    a DID nobody else holds gets you its jobs, and capabilities your guardian
    will refuse.
    """

    def __init__(self, ttl=CLIENT_TTL_SECONDS):
        self._clients = OrderedDict()  # client_id -> record
        self._holders = {}  # asset_did -> client_id: the mapping itself
        self._ttl = ttl
        self._lock = threading.Lock()

    def _online(self, record, now):
        return now - record["last_seen"] <= self._ttl

    def announce(self, *, client_id, asset_did, guardian_url=None, asset_name=None):
        """Record or refresh a client and the DID it holds.

        Returns ``(record, released)``: the stored record, and the
        ``(asset_did, client_id)`` pairs this announcement ended -- this client's
        previous DID if it now holds another, or a quiet holder this client
        replaces. A job addressed to one of those pairs can never be claimed now.

        Raises ``DidHeldElsewhere`` if another connected client holds
        ``asset_did``; nothing is recorded then.
        """
        now = time.time()
        released = []
        with self._lock:
            holder_id = self._holders.get(asset_did)
            if holder_id is not None and holder_id != client_id:
                holder = self._clients[holder_id]
                if self._online(holder, now):
                    raise DidHeldElsewhere(
                        f"{asset_did} is held by FL client {holder_id}, "
                        "which is still connected"
                    )
                # The holder went quiet and this client takes its place. The old
                # record goes with it: a client holds one asset, and this one is
                # no longer that client's.
                logger.warning(
                    "%s moves from client %s (silent for %.0fs) to %s",
                    asset_did,
                    holder_id,
                    now - holder["last_seen"],
                    client_id,
                )
                del self._clients[holder_id]
                released.append((asset_did, holder_id))

            record = self._clients.get(client_id)
            if record is None:
                record = {
                    "client_id": client_id,
                    "asset_did": asset_did,
                    "guardian_url": guardian_url,
                    "asset_name": asset_name,
                    "first_seen": now,
                    "jobs_claimed": 0,
                }
                self._clients[client_id] = record
                logger.info("client %s joined, holding %s", client_id, asset_did)
            elif record["asset_did"] != asset_did:
                # The same client now fronts a different asset -- a guardian
                # redeployed onto the same port. Its old DID is released rather
                # than left resolving to a client that will never claim its jobs.
                logger.warning(
                    "client %s now holds %s (was %s)",
                    client_id,
                    asset_did,
                    record["asset_did"],
                )
                if self._holders.get(record["asset_did"]) == client_id:
                    del self._holders[record["asset_did"]]
                released.append((record["asset_did"], client_id))
                record["asset_did"] = asset_did
            self._holders[asset_did] = client_id

            if guardian_url:
                record["guardian_url"] = guardian_url
            if asset_name:
                record["asset_name"] = asset_name
            record["last_seen"] = now
            return dict(record), released

    def holder(self, asset_did):
        """The connected client holding ``asset_did``, or ``None``."""
        now = time.time()
        with self._lock:
            record = self._clients.get(self._holders.get(asset_did))
            if record is None or not self._online(record, now):
                return None
            return dict(record)

    def claimed_a_job(self, client_id):
        with self._lock:
            record = self._clients.get(client_id)
            if record is not None:
                record["jobs_claimed"] += 1

    def list(self):
        """Every client holding a DID, newest activity first, each flagged online.

        One entry per DID, so the list is the mapping itself. A client that went
        quiet stays listed, offline, until another client takes its DID over.
        """
        now = time.time()
        with self._lock:
            records = [dict(r) for r in self._clients.values()]
        for record in records:
            record["seconds_since_seen"] = round(now - record["last_seen"], 1)
            record["online"] = record["seconds_since_seen"] <= self._ttl
        return sorted(records, key=lambda r: r["last_seen"], reverse=True)

    def online_count(self):
        return sum(1 for r in self.list() if r["online"])


class JobStore:
    """In-memory job queue. Each job is addressed to one client, for one asset.

    The client is the one the DID -> client mapping named when the round was
    submitted. A job moves pending -> running when that client claims it, then to
    complete or failed when it reports back. Nothing is retried and nothing
    expires: a client that claims a job and dies leaves it running forever, which
    is acceptable for a demo and would not be for anything else.
    """

    def __init__(self):
        self._jobs = OrderedDict()
        self._lock = threading.Lock()

    def submit(self, *, round_id, asset_did, client_id, script, capability, script_name=None):
        """Queue one site's job for ``client_id``, the client holding ``asset_did``.

        ``client_id`` is ``None`` when no connected client holds the DID. The job
        is then failed on the spot: it has nobody to go to, and a round waiting
        for it would wait forever.
        """
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id,
            "round_id": round_id,
            "asset_did": asset_did,
            "status": STATUS_PENDING,
            "script": script,
            "capability": capability,
            "script_name": script_name,
            "client_id": client_id,
            "metrics": None,
            "error": None,
        }
        if client_id is None:
            job["status"] = STATUS_FAILED
            job["error"] = f"no FL client holding {asset_did} is connected to this server"
        with self._lock:
            self._jobs[job_id] = job
        if client_id is None:
            logger.warning("job %s for %s failed: no client holds it", job_id, asset_did)
        else:
            logger.info(
                "job %s queued for %s, held by %s (round %s)",
                job_id,
                asset_did,
                client_id,
                round_id,
            )
        return job_id

    def claim_next(self, client_id, asset_did):
        """Hand a client the oldest pending job addressed to it, for the DID it holds."""
        with self._lock:
            for job in self._jobs.values():
                if (
                    job["status"] != STATUS_PENDING
                    or job["client_id"] != client_id
                    or job["asset_did"] != asset_did
                ):
                    continue
                job["status"] = STATUS_RUNNING
                logger.info("job %s claimed by %s", job["job_id"], client_id)
                return {
                    "job_id": job["job_id"],
                    "round_id": job["round_id"],
                    "asset_did": job["asset_did"],
                    "script": job["script"],
                    "capability": job["capability"],
                    "script_name": job["script_name"],
                }
        return None

    def fail_unclaimable(self, asset_did, client_id):
        """Fail the pending jobs addressed to a client that no longer holds the DID.

        Nobody else may claim them -- each capability is for the guardian that
        client was in front of -- so waiting would only hang their rounds.
        """
        failed = []
        with self._lock:
            for job in self._jobs.values():
                if (
                    job["status"] == STATUS_PENDING
                    and job["client_id"] == client_id
                    and job["asset_did"] == asset_did
                ):
                    job["status"] = STATUS_FAILED
                    job["error"] = (
                        f"FL client {client_id} stopped holding {asset_did} "
                        "before claiming this job"
                    )
                    failed.append(job["job_id"])
        for job_id in failed:
            logger.warning("job %s failed: %s no longer holds %s", job_id, client_id, asset_did)

    def report(self, job_id, *, metrics=None, error=None):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if error is not None:
                job["status"] = STATUS_FAILED
                job["error"] = error
            else:
                job["status"] = STATUS_COMPLETE
                job["metrics"] = metrics
            logger.info("job %s reported %s", job_id, job["status"])
            return self._public(job)

    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else self._public(job)

    def count(self):
        with self._lock:
            return len(self._jobs)

    @staticmethod
    def _public(job):
        # the script and the capability are the client's to see, not the
        # submitter's to re-read; a status poll returns neither
        return {k: v for k, v in job.items() if k not in ("script", "capability")}


class RoundStore:
    """Rounds, and what each participant in them reported.

    A round is the requester's unit of work and the only thing it polls. The jobs
    underneath are an implementation detail of fanning it out.
    """

    def __init__(self, jobs):
        self._jobs = jobs
        self._rounds = OrderedDict()
        self._lock = threading.Lock()

    def create(self, *, script, participants, script_name=None, round_name=None):
        """Fan one script out over the participants. Returns the round record.

        Each participant arrives matched to the client holding its DID
        (``client_id``, ``None`` if no connected client does), and its job is
        addressed to that client.
        """
        round_id = uuid.uuid4().hex
        job_ids = OrderedDict()
        for participant in participants:
            job_ids[participant["asset_did"]] = self._jobs.submit(
                round_id=round_id,
                asset_did=participant["asset_did"],
                client_id=participant["client_id"],
                script=script,
                capability=participant["capability"],
                script_name=script_name,
            )
        with self._lock:
            self._rounds[round_id] = {
                "round_id": round_id,
                "round_name": round_name,
                "script_name": script_name,
                "created": time.time(),
                "job_ids": job_ids,
            }
        logger.info(
            "round %s submitted (%s) over %d site(s)",
            round_id,
            script_name or "unnamed script",
            len(job_ids),
        )
        return self.get(round_id)

    def get(self, round_id):
        with self._lock:
            record = self._rounds.get(round_id)
            if record is None:
                return None
            record = dict(record)
            record["job_ids"] = OrderedDict(record["job_ids"])

        participants = []
        for asset_did, job_id in record["job_ids"].items():
            job = self._jobs.get(job_id) or {}
            participants.append(
                {
                    "asset_did": asset_did,
                    "job_id": job_id,
                    "client_id": job.get("client_id"),
                    "status": job.get("status"),
                    "metrics": job.get("metrics"),
                    "error": job.get("error"),
                }
            )

        statuses = [p["status"] for p in participants]
        if all(s in TERMINAL_STATUSES for s in statuses):
            # A round is complete when every site has answered; it failed only if
            # none of them managed to run. One site refusing is a result about
            # that site, not a broken round.
            status = (
                STATUS_COMPLETE
                if any(s == STATUS_COMPLETE for s in statuses)
                else STATUS_FAILED
            )
        elif any(s == STATUS_RUNNING for s in statuses):
            status = STATUS_RUNNING
        else:
            status = STATUS_PENDING

        return {
            "round_id": record["round_id"],
            "round_name": record["round_name"],
            "script_name": record["script_name"],
            "created": record["created"],
            "status": status,
            "participants": participants,
            "aggregate": aggregate_metrics(participants),
        }

    def count(self):
        with self._lock:
            return len(self._rounds)


def aggregate_metrics(participants):
    """Combine what the sites reported into one result for the round.

    This is the only thing here that is recognisably an *aggregator*: metrics come
    back per site and are averaged into one number, weighted by how much data each
    site ran over, which is what federated averaging does with model updates. No
    site's rows were ever seen to compute it.
    """
    reported = [p["metrics"] for p in participants if isinstance(p.get("metrics"), dict)]
    if not reported:
        return None

    total_samples = sum(m.get("samples") or 0 for m in reported)
    aggregate = {
        "sites": len(reported),
        "sites_failed": sum(1 for p in participants if p.get("status") == STATUS_FAILED),
        "total_samples": total_samples,
    }

    for key in ("accuracy", "loss"):
        values = [(m.get(key), m.get("samples") or 0) for m in reported if key in m]
        values = [(v, w) for v, w in values if isinstance(v, (int, float))]
        if not values:
            continue
        weight = sum(w for _, w in values)
        if weight:
            aggregate[key] = round(sum(v * w for v, w in values) / weight, 4)
        else:
            aggregate[key] = round(sum(v for v, _ in values) / len(values), 4)

    return aggregate


class FLServerHandler(BaseHTTPRequestHandler):
    server_version = f"{SERVICE_NAME}/0.2"

    # -----------------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        query = parse_qs(url.query)

        if path == "/info":
            self._respond(
                {
                    "service": SERVICE_NAME,
                    "clients": self.server.clients.online_count(),
                    "rounds": self.server.rounds.count(),
                    "jobs": self.server.jobs.count(),
                }
            )
        elif path == "/clients":
            self._respond({"clients": self.server.clients.list()})
        elif path == "/jobs/next":
            self._claim_job(query)
        elif path.startswith("/rounds/"):
            record = self.server.rounds.get(path[len("/rounds/") :])
            if record is None:
                self._respond({"error": "unknown round"}, HTTPStatus.NOT_FOUND)
            else:
                self._respond(record)
        elif path.startswith("/jobs/"):
            job = self.server.jobs.get(path[len("/jobs/") :])
            if job is None:
                self._respond({"error": "unknown job"}, HTTPStatus.NOT_FOUND)
            else:
                self._respond(job)
        else:
            self._respond({"error": f"unknown path: {path}"}, HTTPStatus.NOT_FOUND)

    # -----------------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        body = self._read_json()
        if body is None:
            self._respond({"error": "invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/clients":
            self._announce_client(body)
        elif path == "/rounds":
            self._submit_round(body)
        elif path.startswith("/jobs/") and path.endswith("/metrics"):
            self._report_job(path[len("/jobs/") : -len("/metrics")], body)
        else:
            self._respond({"error": f"unknown path: {path}"}, HTTPStatus.NOT_FOUND)

    # -----------------------------------------------------------------
    # The DID -> client mapping is read and changed under ``server.routing``:
    # a client announcing, a client claiming, and a round being matched to
    # clients. Held across each of those whole, a round cannot be matched to a
    # client in the instant that client stops holding the DID, which would leave
    # a job addressed to nobody.
    # -----------------------------------------------------------------
    def _register(self, client_id, asset_did, **details):
        """Announce a client, failing any jobs its announcement orphans.

        Must be called under ``server.routing``. Raises ``DidHeldElsewhere``.
        """
        record, released = self.server.clients.announce(
            client_id=client_id, asset_did=asset_did, **details
        )
        for did, former in released:
            self.server.jobs.fail_unclaimable(did, former)
        return record

    def _announce_client(self, body):
        client_id = (body.get("client_id") or "").strip()
        asset_did = (body.get("asset_did") or "").strip()
        if not client_id or not asset_did:
            self._respond(
                {"error": "'client_id' and 'asset_did' are both required"},
                HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            with self.server.routing:
                record = self._register(
                    client_id,
                    asset_did,
                    guardian_url=body.get("guardian_url"),
                    asset_name=body.get("asset_name"),
                )
        except DidHeldElsewhere as e:
            self._respond({"error": str(e)}, HTTPStatus.CONFLICT)
            return
        self._respond({"ok": True, "client": record})

    def _claim_job(self, query):
        client_id = (query.get("client_id") or [""])[0]
        asset_did = (query.get("asset_did") or [""])[0]
        if not client_id or not asset_did:
            self._respond(
                {"error": "'client_id' and 'asset_did' are both required"},
                HTTPStatus.BAD_REQUEST,
            )
            return

        # A poll is also a heartbeat: a client that is asking for work is a client
        # that is connected, so nothing has to keep a separate registration alive.
        # It is refused exactly as an announcement would be, and a refused client
        # gets no work.
        try:
            with self.server.routing:
                self._register(client_id, asset_did)
                job = self.server.jobs.claim_next(client_id, asset_did)
        except DidHeldElsewhere as e:
            self._respond({"error": str(e)}, HTTPStatus.CONFLICT)
            return
        if job is not None:
            self.server.clients.claimed_a_job(client_id)
        self._respond({"job": job})

    def _submit_round(self, body):
        script = body.get("script")
        participants = body.get("participants")
        if not isinstance(script, str) or not script.strip():
            self._respond({"error": "'script' must be a non-empty string"}, HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(participants, list) or not participants:
            self._respond(
                {"error": "'participants' must be a non-empty list"},
                HTTPStatus.BAD_REQUEST,
            )
            return

        seen = set()
        cleaned = []
        for participant in participants:
            if not isinstance(participant, dict):
                self._respond({"error": "each participant must be an object"}, HTTPStatus.BAD_REQUEST)
                return
            asset_did = (participant.get("asset_did") or "").strip()
            capability = participant.get("capability")
            if not asset_did:
                self._respond(
                    {"error": "each participant needs an 'asset_did'"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            if not isinstance(capability, dict) or not capability:
                self._respond(
                    {"error": f"participant {asset_did} needs a 'capability' object"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            # Two jobs for one site in one round would have that site racing
            # itself for two capabilities, and the round would never be able to
            # say which result was which.
            if asset_did in seen:
                self._respond(
                    {"error": f"{asset_did} appears twice in this round"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            seen.add(asset_did)
            cleaned.append({"asset_did": asset_did, "capability": capability})

        # Match each capability to the client holding the DID it was minted for.
        # The submitter names assets, never clients: which client holds what is
        # this server's to know, from what the clients themselves announced.
        with self.server.routing:
            for participant in cleaned:
                holder = self.server.clients.holder(participant["asset_did"])
                participant["client_id"] = holder["client_id"] if holder else None
            record = self.server.rounds.create(
                script=script,
                participants=cleaned,
                script_name=body.get("script_name"),
                round_name=body.get("round_name"),
            )
        self._respond(record, HTTPStatus.CREATED)

    def _report_job(self, job_id, body):
        error = body.get("error")
        metrics = body.get("metrics")
        if error is None and not isinstance(metrics, dict):
            self._respond(
                {"error": "one of 'metrics' (object) or 'error' is required"},
                HTTPStatus.BAD_REQUEST,
            )
            return

        job = self.server.jobs.report(job_id, metrics=metrics, error=error)
        if job is None:
            self._respond({"error": "unknown job"}, HTTPStatus.NOT_FOUND)
        else:
            self._respond({"job_id": job_id, "status": job["status"]})

    # -----------------------------------------------------------------
    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _respond(self, body, status=HTTPStatus.OK):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        # The webapp reads this server from the browser as well as from its own
        # process, and the two are not the same origin.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def serve(interface, port):
    httpd = ThreadingHTTPServer((interface, port), FLServerHandler)
    httpd.jobs = JobStore()
    httpd.rounds = RoundStore(httpd.jobs)
    httpd.clients = ClientRegistry()
    httpd.routing = threading.Lock()
    logger.info("%s listening on %s:%d", SERVICE_NAME, interface, port)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Run the mock FL server.")
    parser.add_argument(
        "-n", "--interface", default="0.0.0.0", help="interface to bind (default: 0.0.0.0)"
    )
    parser.add_argument("-p", "--port", type=int, default=7920, help="port to bind (default: 7920)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    serve(args.interface, args.port)


if __name__ == "__main__":
    main()
