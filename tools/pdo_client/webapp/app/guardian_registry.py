"""Discovery of the guardian types an asset can be put behind.

A guardian is a folder under ``GUARDIANS_DIR`` holding a ``run.sh`` and a
``guardian.json`` manifest. The manifest says how to start it — which options its
``run.sh`` takes and where each option's value comes from — so the webapp learns
what guardians exist by reading the folder rather than by naming them in code.

Manifest fields::

    type          identifier stored on the asset and used everywhere else
    title         short human label for the registration form
    description   one line explaining what the guardian does
    order         sort position in the form (default 100)
    image         optional {env, default}: Docker image, overridable by env var
    options       {run.sh option: value name}, in the order they are passed

An option's value name must be one of :data:`LAUNCH_VALUES` — the vocabulary the
launcher offers. A guardian that needs something outside that vocabulary needs a
new entry there as well as in its manifest.

Adding a guardian is dropping in a folder. Making it *usable* also needs a runner
in ``app.action_runners`` keyed by the same ``type``, because how a consumer drives
a guardian is behaviour, not configuration.
"""

import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

MANIFEST_NAME = "guardian.json"

# The values a manifest's options may draw on. The launcher computes all of them
# for every guardian; a manifest names the ones its run.sh actually takes.
LAUNCH_VALUES = (
    "data_path",  # host path of the file the guardian serves
    "bind_interface",  # interface to listen on
    "advertised_host",  # host others use to reach it
    "port",  # port to publish
    "storage_port",  # the paired PDO storage service port
    "image",  # Docker image, from the manifest's image block
    "fl_server_url",  # FL server, as addressable from inside the guardian
    "fl_client_id",  # name the guardian's FL client is known by
    "asset_did",  # DID of the asset this guardian is being started for
    "asset_name",  # that asset's display name
)


class Manifest:
    """One guardian type, as described by its folder."""

    def __init__(self, directory, data):
        self.directory = directory
        self.type = data["type"]
        self.title = data.get("title") or self.type
        self.description = data.get("description", "")
        self.order = data.get("order", 100)
        self.options = data.get("options") or {}
        self._image = data.get("image") or {}

    @property
    def run_script(self):
        return os.path.join(self.directory, "run.sh")

    @property
    def image(self):
        """The Docker image to run, or ``None`` for a guardian that needs no image.

        The manifest names the environment variable that overrides it, so a
        deployment can point a guardian at a different image without the webapp
        knowing which guardians have images at all.
        """
        if not self._image:
            return None
        return os.environ.get(self._image.get("env", ""), self._image.get("default"))

    def validate(self):
        """Raise ``ValueError`` if this manifest cannot be launched as written."""
        if not self.options:
            raise ValueError(f"guardian {self.type!r} declares no run.sh options")
        unknown = sorted(set(self.options.values()) - set(LAUNCH_VALUES))
        if unknown:
            raise ValueError(
                f"guardian {self.type!r} asks for unknown launch value(s): "
                f"{', '.join(unknown)}"
            )
        if "image" in self.options.values() and not self.image:
            raise ValueError(f"guardian {self.type!r} needs an image but declares none")
        if not os.path.isfile(self.run_script):
            raise ValueError(f"guardian {self.type!r} has no run.sh at {self.run_script}")


def _load(directory):
    path = os.path.join(directory, MANIFEST_NAME)
    with open(path) as f:
        return Manifest(directory, json.load(f))


def manifests():
    """Every guardian found under ``GUARDIANS_DIR``, in form order.

    A folder without a manifest is not a guardian and is skipped silently; a folder
    with a manifest that cannot be read or does not validate is logged and skipped,
    so one broken guardian does not take down the registration form.
    """
    root = settings.GUARDIANS_DIR
    found = []
    try:
        entries = sorted(os.scandir(root), key=lambda e: e.name)
    except OSError as e:
        logger.error("Cannot read the guardians directory %s: %s", root, e)
        return found

    for entry in entries:
        if not entry.is_dir() or not os.path.isfile(
            os.path.join(entry.path, MANIFEST_NAME)
        ):
            continue
        try:
            manifest = _load(entry.path)
            manifest.validate()
        except (OSError, ValueError, KeyError) as e:
            logger.error("Ignoring guardian in %s: %s", entry.path, e)
            continue
        found.append(manifest)

    return sorted(found, key=lambda m: (m.order, m.type))


def get(guardian_type):
    """Return the manifest for a guardian type, or raise ``ValueError``."""
    for manifest in manifests():
        if manifest.type == guardian_type:
            return manifest
    raise ValueError(f"unknown guardian type: {guardian_type!r}")


def types():
    """The guardian types available, in form order."""
    return [m.type for m in manifests()]
