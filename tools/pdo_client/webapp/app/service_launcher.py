"""Starting a service whose ``run.sh`` lives in this repo.

Two kinds of service are started this way — the guardian in front of an asset,
and the FL server a federation gathers around — and what differs between them is
only which script is run with which options. What they share is the awkward part:
*where* the command has to run.

* Not containerized (``CONTAINERIZED_DEPLOYMENT`` off): the webapp has Docker
  access and runs the command itself as a detached subprocess.
* Containerized (``CONTAINERIZED_DEPLOYMENT`` on): the webapp has no Docker
  access, so it writes the command as a shell script into ``GUARDIAN_DEPLOY_DIR``
  (a directory shared with the host); the host-side launcher watches that
  directory and runs each script. That is what keeps a container from having to
  start containers.

Either way the command is a ``run.sh`` invocation, so nothing about how a
particular service is actually launched is duplicated here.

After dispatching, poll :func:`wait_until_healthy` — every service in this repo
answers ``GET /info`` once it is up, and that is the only endpoint they all share.
"""

import logging
import os
import subprocess
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def dispatch(command, *, log_name):
    """Start a service, here or on the host, depending on where we are running.

    Does not wait for it to be ready — call :func:`wait_until_healthy` for that.
    """
    if settings.CONTAINERIZED_DEPLOYMENT:
        _write_deploy_request(command)
    else:
        _run_command(command, log_name)


def _write_deploy_request(command):
    """Drop the command into GUARDIAN_DEPLOY_DIR for the host watcher.

    Written atomically (temp file + rename) so the watcher never reads a
    half-written script.
    """
    deploy_dir = settings.GUARDIAN_DEPLOY_DIR
    os.makedirs(deploy_dir, exist_ok=True)
    name = f"service_{os.urandom(6).hex()}.sh"
    final_path = os.path.join(deploy_dir, name)
    tmp_path = final_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write("#!/usr/bin/env bash\n" + command + "\n")
    os.rename(tmp_path, final_path)
    logger.info("Wrote deploy request: %s", final_path)


def _run_command(command, log_name):
    """Run the command as a detached background process.

    A run.sh blocks for the service's lifetime, so it is deliberately not waited
    on; readiness is confirmed separately via wait_until_healthy.
    """
    log_path = os.path.join(settings.SCRATCH_DIR, log_name)
    logger.info("Running service command (log: %s)", log_path)
    log_file = open(log_path, "ab")
    subprocess.Popen(
        ["bash", "-c", command],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def wait_until_healthy(url, timeout=120, interval=3):
    """Poll a service's ``/info`` until it responds 200, or raise.

    Raises ``TimeoutError`` if it is not healthy within ``timeout`` seconds.
    """
    info_url = f"{url.rstrip('/')}/info"
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(info_url, timeout=5)
            if resp.status_code == 200:
                logger.info("Healthy at %s", info_url)
                return
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            last_error = str(e)
        time.sleep(interval)
    raise TimeoutError(
        f"Nothing became healthy at {info_url} within {timeout}s "
        f"(last error: {last_error})"
    )
