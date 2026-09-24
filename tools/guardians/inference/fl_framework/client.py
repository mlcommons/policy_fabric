"""A mock federated-learning client, running beside the guardian core.

This stands in for the FL framework a data holder would run inside their own
environment. **It holds the data**: the dataset is mounted into this client, not
into the guardian. It never listens for work: it announces itself to an FL server
and then polls it, and each job it gets back carries the script to run together
with the capability package authorizing that run.

**It announces which asset it holds.** A client sits in front of exactly one
dataset, and that dataset is an asset with a DID. It joins under its own ID and
reports that DID with it, and the server keeps the pair: which client holds which
DID. That mapping is what lets the server show a requester which sites are
connected, and -- once the requester has picked some -- match each capability,
by the DID it was minted for, to the one client holding it. A capability is
worth nothing at any other guardian, so an unlabelled client could only ever be
handed work it would fail.

**It asks before it runs.** The client hashes the script it actually holds and
sends that digest, with the capability, to the guardian core over localhost. The
core answers yes or no: yes only when the digest the capability authorizes is the
one the client computed. On a yes the client reads its own data and runs; on
anything else it reports the job failed and never opens the file. Everything
after that is simulated -- the client prints what it would run and reports fixed
metrics.

The client deliberately depends on nothing from PDO. A real FL framework would
not be a PDO component either; all it has to know is how to POST a capability
package to a guardian and read back a yes or a no.
"""

import hashlib
import logging
import time

import requests

logger = logging.getLogger(__name__)

DIGEST_PREFIX = "sha256:"


def script_digest(script):
    """Return the digest naming a script, in the form the policy records.

    The prefix names the algorithm, so a capability stays readable about what it
    committed to and a later change of algorithm cannot be mistaken for a match.
    """
    return DIGEST_PREFIX + hashlib.sha256(script.encode("utf-8")).hexdigest()


class NotAllowed(Exception):
    """The guardian core did not say yes to this job."""


class Refused(Exception):
    """The FL server would not register this client, and said why."""


class FLClient:
    """Poll an FL server for jobs and run each one the local guardian allows."""

    def __init__(
        self,
        *,
        server_url,
        guardian_url,
        client_id,
        asset_did,
        data_path,
        asset_name=None,
        poll_interval=3.0,
        announce_interval=30.0,
        timeout=30.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.guardian_url = guardian_url.rstrip("/")
        self.client_id = client_id
        self.asset_did = asset_did
        self.data_path = data_path
        self.asset_name = asset_name
        self.poll_interval = poll_interval
        self.announce_interval = announce_interval
        self.timeout = timeout

    # -----------------------------------------------------------------
    # FL server
    # -----------------------------------------------------------------
    def announce(self):
        """Tell the server this client is here, and which asset it holds.

        Polling refreshes the same registration, so this matters for two things:
        being *listed* promptly when the client starts, and being listed *fully*
        after the server has restarted. A poll carries only the client's ID and
        its DID, which is all the routing needs; this carries the rest.
        """
        resp = requests.post(
            f"{self.server_url}/clients",
            json={
                "client_id": self.client_id,
                "asset_did": self.asset_did,
                "asset_name": self.asset_name,
                "guardian_url": self.guardian_url,
            },
            timeout=self.timeout,
        )
        _raise_if_refused(resp)
        resp.raise_for_status()
        return resp.json()

    def poll_job(self):
        """Ask the server for the next job addressed to this client, or ``None``."""
        resp = requests.get(
            f"{self.server_url}/jobs/next",
            params={"client_id": self.client_id, "asset_did": self.asset_did},
            timeout=self.timeout,
        )
        _raise_if_refused(resp)
        resp.raise_for_status()
        return resp.json().get("job")

    def report_metrics(self, job_id, metrics):
        """Report a finished run back to the server."""
        resp = requests.post(
            f"{self.server_url}/jobs/{job_id}/metrics",
            json={"client_id": self.client_id, "metrics": metrics},
            timeout=self.timeout,
        )
        resp.raise_for_status()

    def report_failure(self, job_id, error):
        """Report a run that never happened, so the round stops waiting on it."""
        resp = requests.post(
            f"{self.server_url}/jobs/{job_id}/metrics",
            json={"client_id": self.client_id, "error": str(error)},
            timeout=self.timeout,
        )
        resp.raise_for_status()

    # -----------------------------------------------------------------
    # guardian core
    # -----------------------------------------------------------------
    def ask_guardian(self, capability, calculated_digest):
        """Ask the local guardian core whether this script may run. Raise if not.

        ``calculated_digest`` is this client's own measurement of the script it
        holds; the guardian core compares it against the digest the capability
        authorizes. Yes is HTTP 200 with ``{"allowed": true}``; no is an error
        response (HTTP 422 for a digest mismatch). A request the core could not
        process at all -- a capability minted for another guardian, one that does
        not validate -- is as much a no as a mismatch.
        """
        request = dict(capability)
        request["request_context"] = {"calculated_script_digest": calculated_digest}

        resp = requests.post(
            f"{self.guardian_url}/process_capability", json=request, timeout=self.timeout
        )
        if resp.status_code != 200:
            raise NotAllowed(f"the guardian said no ({_error_text(resp)})")

        answer = resp.json()
        if not (isinstance(answer, dict) and answer.get("allowed") is True):
            raise NotAllowed(f"the guardian did not say yes: {answer}")
        return answer

    # -----------------------------------------------------------------
    # the run itself
    # -----------------------------------------------------------------
    def load_data(self):
        """Read the dataset this client holds.

        Read per job, and only once the guardian has said yes, so that a job the
        guardian refused never touches the data at all.
        """
        with open(self.data_path) as f:
            return f.read()

    def run_script(self, job, script, data):
        """Stand in for executing the script over the data.

        A real client hands both to the training framework here. This one narrates
        the run and returns fixed metrics, which is enough to show the code reaching
        the data without the data ever leaving the data holder.
        """
        print(
            f"[fl_client:{self.client_id}] running job {job['job_id']} "
            f"({len(script)} bytes of script) over {len(data)} bytes of data "
            f"held as {self.asset_did}"
        )
        return {
            "accuracy": 0.42,
            "loss": 1.23,
            "samples": len(data),
            "client_id": self.client_id,
            "asset_did": self.asset_did,
        }

    def handle_job(self, job):
        """Run one job end to end: measure, ask, run, report."""
        job_id = job["job_id"]
        script = job["script"]
        capability = job["capability"]

        digest = script_digest(script)
        logger.info("job %s: computed script digest %s", job_id, digest)

        try:
            self.ask_guardian(capability, digest)
        except Exception as e:
            logger.warning("job %s: not allowed to run: %s", job_id, e)
            self.report_failure(job_id, f"not allowed to run: {e}")
            return
        logger.info("job %s: the guardian allowed %s", job_id, digest)

        metrics = self.run_script(job, script, self.load_data())
        self.report_metrics(job_id, metrics)
        logger.info("job %s: reported metrics %s", job_id, metrics)

    def _announce_quietly(self):
        """Announce, and carry on if the server is not there to hear it."""
        try:
            self.announce()
            logger.info("announced %s to the FL server", self.asset_did)
        except Refused as e:
            logger.warning("the FL server refused this client (%s); polling anyway", e)
        except Exception as e:
            logger.warning("could not announce to the FL server (%s); polling anyway", e)

    # -----------------------------------------------------------------
    def run_forever(self):
        """Announce, then poll for jobs until interrupted.

        A polling error is logged and retried rather than fatal: the FL server
        coming up after the client is the normal case in a demo. The announcement
        is repeated on a slower clock for the same reason -- a server that has
        been restarted has never heard of this site, and a poll alone tells it
        only the two things routing needs.
        """
        logger.info(
            "fl client %s (holding %s at %s) polling %s every %ss, guardian at %s",
            self.client_id,
            self.asset_did,
            self.data_path,
            self.server_url,
            self.poll_interval,
            self.guardian_url,
        )
        self._announce_quietly()
        announced_at = time.monotonic()

        while True:
            if time.monotonic() - announced_at >= self.announce_interval:
                self._announce_quietly()
                announced_at = time.monotonic()

            try:
                job = self.poll_job()
            except Refused as e:
                logger.warning("the FL server refused this client (%s); retrying", e)
                job = None
            except Exception as e:
                logger.warning("could not reach the FL server (%s); retrying", e)
                job = None

            if job is None:
                time.sleep(self.poll_interval)
                continue

            try:
                self.handle_job(job)
            except Exception:
                logger.exception("job %s failed", job.get("job_id"))


def _error_text(resp):
    """The error a guardian returned, as briefly as it can be said."""
    text = (resp.text or "").strip()
    return f"HTTP {resp.status_code}: {text[:200]}" if text else f"HTTP {resp.status_code}"


def _raise_if_refused(resp):
    """Raise ``Refused`` if the FL server turned this client away.

    It does that (409) when another connected client already holds this DID. The
    server is up and answering then, and a log saying it could not be reached
    would send whoever reads it looking in the wrong place.
    """
    if resp.status_code == 409:
        try:
            reason = resp.json().get("error")
        except ValueError:
            reason = None
        raise Refused(reason or _error_text(resp))
