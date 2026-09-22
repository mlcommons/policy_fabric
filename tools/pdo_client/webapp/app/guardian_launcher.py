"""Start a guardian for an asset.

Registering an asset also deploys a guardian for it. The owner chooses which kind,
where it listens (``settings.SERVE_ON_CHOICES``), and on which port. Each kind owns
a ``run.sh`` and a manifest saying which options that script takes (see
``app.guardian_registry``), so this module never names a guardian: it computes the
values a launch could need and lets each manifest pick the ones it wants.

Where the resulting command is actually *run* — here, or on the host when this
webapp is itself in a container — is not a guardian question and lives in
``app.service_launcher``, which the FL server's launcher uses too.

After deploying, poll ``wait_until_healthy`` until the guardian's ``/info``
endpoint responds — every guardian answers it.
"""

import logging
import shlex
import socket

from django.conf import settings

from . import guardian_registry, service_launcher

logger = logging.getLogger(__name__)


def resolve_serve_on(serve_on):
    """Map a ``serve_on`` choice to ``(bind_interface, advertised_host)``.

    ``bind_interface`` is what the guardian listens on; ``advertised_host`` is the
    host recorded on the asset and burned into the token contract, so it must be
    an address the requester and the policy author can actually reach.
    """
    if serve_on == "localhost":
        return "127.0.0.1", "localhost"
    if serve_on == "0.0.0.0":
        return "0.0.0.0", settings.F_SERVICE_HOST
    if serve_on == "HOSTNAME":
        return "0.0.0.0", socket.gethostname()
    raise ValueError(f"unknown serve_on: {serve_on!r}")


def fl_client_id(host, port):
    """The name an FL client beside a guardian on ``host:port`` is known by.

    An inference guardian ships with an FL client, and that client shows up on the
    FL server's list of connected sites. Naming it after the guardian's own
    address makes the list legible when several are up, without either side
    storing anything extra. Nothing is routed by this name -- work is addressed to
    the asset's DID -- so it is a label, not an identifier anything depends on.
    """
    return f"{host}:{port}"


def _storage_port(port):
    """The PDO storage service port that pairs with a guardian on ``port``.

    Derived rather than configured so two guardians on different ports do not
    collide on one shared storage port. Guardians that need no storage service
    simply never ask for this value.
    """
    return int(port) + 1


def launch_values(manifest, data_path, *, serve_on, port, asset_did="", asset_name=""):
    """Everything a launch could need, for a manifest to draw the parts it takes.

    The keys are ``guardian_registry.LAUNCH_VALUES``; a manifest that names one
    outside that set is rejected when it is loaded, so anything reachable here is
    known to exist.
    """
    bind_interface, advertised_host = resolve_serve_on(serve_on)
    return {
        "data_path": data_path,
        "bind_interface": bind_interface,
        "advertised_host": advertised_host,
        "port": str(port),
        "storage_port": str(_storage_port(port)),
        "image": manifest.image,
        "fl_server_url": settings.FL_SERVER_URL_FROM_GUARDIAN,
        "fl_client_id": fl_client_id(advertised_host, port),
        "asset_did": asset_did,
        "asset_name": asset_name,
    }


def guardian_run_command(
    data_path, *, guardian_type, serve_on, port, asset_did="", asset_name=""
):
    """Return ``(command, advertised_host, port)`` for one guardian.

    ``command`` is the ``run.sh`` invocation that starts a guardian of
    ``guardian_type`` serving ``data_path``, with exactly the options its manifest
    declares, in the order it declares them. Every value is quoted: a data path or
    an asset name is whatever its owner typed, and this string is run by a shell.
    """
    manifest = guardian_registry.get(guardian_type)
    values = launch_values(
        manifest,
        data_path,
        serve_on=serve_on,
        port=port,
        asset_did=asset_did,
        asset_name=asset_name,
    )

    parts = [f"bash {shlex.quote(manifest.run_script)}"]
    for option, value_name in manifest.options.items():
        parts.append(f"    {option} {shlex.quote(values[value_name])}")

    return " \\\n".join(parts), values["advertised_host"], values["port"]


def deploy_guardian(
    data_path, *, guardian_type, serve_on, port, asset_did="", asset_name=""
):
    """Start a guardian serving ``data_path`` and return ``(host, port)``.

    ``asset_did`` names the asset this guardian is being started for. An inference
    guardian passes it to its FL client, which announces it to the FL server — so
    the guardian has to be started *after* the asset's identity contract exists,
    and a site that is up but nameless is a site no round can be addressed to.

    Does not wait for the guardian to be ready — call ``wait_until_healthy``.
    """
    command, host, port = guardian_run_command(
        data_path,
        guardian_type=guardian_type,
        serve_on=serve_on,
        port=port,
        asset_did=asset_did,
        asset_name=asset_name,
    )
    service_launcher.dispatch(command, log_name="guardian_run.log")
    return host, port


def wait_until_healthy(host, port, timeout=120, interval=3):
    """Poll the guardian's ``/info`` until it responds 200, or raise.

    A 200 from ``/info`` means the guardian service is listening and ready.
    Raises ``TimeoutError`` if the guardian is not healthy within ``timeout``
    seconds.
    """
    service_launcher.wait_until_healthy(
        f"http://{host}:{port}", timeout=timeout, interval=interval
    )
