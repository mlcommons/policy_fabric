"""A mock federated-learning client, running beside the guardian core.

This stands in for the FL framework a data holder would run inside their own
environment. It never listens for work: it announces itself to an FL server and
then polls it, and each job it gets back carries the script to run together with
the capability package authorizing that run.

**It announces which asset it holds.** A client sits in front of exactly one
dataset, and that dataset is an asset with a DID. Reporting that DID when it
joins is what lets the server show a requester which sites are connected, and --
once the requester has picked some -- hand each client the capability minted for
*its* guardian. A capability is worth nothing at any other guardian, so an
unlabelled client could only ever be handed work it would fail.

The client is also the party that turns a claim about code into a fact about
code. It hashes the script it actually holds and presents that digest with the
capability to the guardian core over localhost; the guardian core releases the
data only when the digest matches the one the capability authorizes. Everything
after that is simulated -- the client prints what it would run and reports fixed
metrics.

The client deliberately depends on nothing from PDO. A real FL framework would
not be a PDO component either; all it has to know is how to POST a capability
package to a guardian.
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


class FLClient:
    """Poll an FL server for jobs and run each one against the local guardian."""

    def __init__(
        self,
        *,
        server_url,
        guardian_url,
        client_id,
        asset_did,
        asset_name=None,
        poll_interval=3.0,
        announce_interval=30.0,
        timeout=30.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.guardian_url = guardian_url.rstrip("/")
        self.client_id = client_id
        self.asset_did = asset_did
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
        after the server has restarted. A poll carries only the client's name and
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
        resp.raise_for_status()
        return resp.json()

    def poll_job(self):
        """Ask the server for the next pending job, or ``None`` if there is none."""
        resp = requests.get(
            f"{self.server_url}/jobs/next",
            params={"client_id": self.client_id, "asset_did": self.asset_did},
            timeout=self.timeout,
        )
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
    def fetch_data(self, capability, calculated_digest):
        """Redeem a capability at the local guardian core and return the asset.

        ``calculated_digest`` is this client's own measurement of the script it
        holds; the guardian core compares it against the digest the capability
        authorizes and refuses the request if they differ.
        """
        request = dict(capability)
        request["request_context"] = {"calculated_script_digest": calculated_digest}

        resp = requests.post(
            f"{self.guardian_url}/process_capability", json=request, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    # -----------------------------------------------------------------
    # the run itself
    # -----------------------------------------------------------------
    def run_script(self, job, script, data):
        """Stand in for executing the script over the data.

        A real client hands both to the training framework here. This one narrates
        the run and returns fixed metrics, which is enough to show the data
        reaching the compute without ever leaving the guardian's host.
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
        """Run one job end to end: measure, redeem, run, report."""
        job_id = job["job_id"]
        script = job["script"]
        capability = job["capability"]

        digest = script_digest(script)
        logger.info("job %s: computed script digest %s", job_id, digest)

        try:
            data = self.fetch_data(capability, digest)
        except Exception as e:
            logger.exception("job %s: guardian refused the capability", job_id)
            self.report_failure(job_id, f"guardian refused the capability: {e}")
            return

        metrics = self.run_script(job, script, data)
        self.report_metrics(job_id, metrics)
        logger.info("job %s: reported metrics %s", job_id, metrics)

    def _announce_quietly(self):
        """Announce, and carry on if the server is not there to hear it."""
        try:
            self.announce()
            logger.info("announced %s to the FL server", self.asset_did)
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
            "fl client %s (holding %s) polling %s every %ss, guardian at %s",
            self.client_id,
            self.asset_did,
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
