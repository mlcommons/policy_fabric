"""Start an FL server on the host this webapp is running on.

A federated round goes to an FL server that is **already there**: it is a
long-lived service several data holders connect to, chosen by whoever asks for
the round, and nothing about using an asset starts one. What this module is for
is the case before any of that — the address this deployment is pointed at has
nothing answering on it, and there is no one else to ask.

It is the same launch path a guardian takes (see ``app.service_launcher``): the
command is an invocation of ``tools/fl_server/run.sh``, which runs the server as a
container. When the webapp is itself containerized it cannot run that, so it
writes the command out and the host-side watcher runs it — which is how a
container gets a sibling container started without a Docker socket inside it.

Only the address this deployment was configured with can be started here. An FL
server somewhere else is somebody else's to run, and a page offering to start one
would be lying about what it can reach.
"""

import logging
import os
import shlex
from urllib.parse import urlparse

from django.conf import settings

from . import service_launcher

logger = logging.getLogger(__name__)

DEFAULT_PORT = 7920


def local_server_url():
    """The FL server address this deployment can start for itself."""
    return settings.FL_SERVER_URL


def is_local(server_url):
    """Whether ``server_url`` is the one this deployment could start."""
    return server_url.rstrip("/") == local_server_url().rstrip("/")


def _port():
    """The host port to publish it on, taken from the address we will look for."""
    return urlparse(local_server_url()).port or DEFAULT_PORT


def _run_script():
    return os.path.join(settings.FL_SERVER_DIR, "run.sh")


def launch_command():
    """The ``run.sh`` invocation that starts the FL server."""
    return " \\\n".join(
        [
            f"bash {shlex.quote(_run_script())}",
            f"    --image {shlex.quote(settings.FL_SERVER_IMAGE)}",
            "    --interface 0.0.0.0",
            f"    --port {_port()}",
        ]
    )


def deploy():
    """Start the FL server and return the URL it will answer on.

    Does not wait for it — call ``service_launcher.wait_until_healthy`` on the
    returned URL.
    """
    # The path is a *host* path when this webapp is containerized, so there is
    # nothing here that could check it; the host watcher fails loudly instead.
    if not settings.CONTAINERIZED_DEPLOYMENT and not os.path.isfile(_run_script()):
        raise ValueError(
            f"No FL server run.sh at {_run_script()}; set FL_SERVER_DIR to the "
            "folder holding it."
        )
    command = launch_command()
    logger.info("Starting an FL server:\n%s", command)
    service_launcher.dispatch(command, log_name="fl_server_run.log")
    return local_server_url()
