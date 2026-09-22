"""Consumer flows, one per guardian type.

An asset is used through whatever the guardian in front of it will do, and each
guardian type asks for something different. A public guardian hands the file to
anyone who asks. A download guardian gives back bytes encrypted to the requester's
own key. An inference guardian gives back nothing at all — the data stays where it
is and a script is run against it, and what returns is metrics.

The two policy-gated ones share a front half — a policy decision credential and the
capability that follows from it — and differ in what happens to that capability.

A runner owns one guardian type end to end: what the Use form must collect, what
the flow's steps are, and what the result looks like. Adding a guardian type means
writing a runner and listing it in ``RUNNERS``, not branching inside a view.

Each runner exposes ``steps()`` as the ``(id, label, fn)`` triples
``app.views._streaming.stream_steps`` runs, so the same definition drives both the
streaming and the plain JSON endpoint.

One runner is marked ``federated``. An inference asset is not used on its own: the
point of keeping data in place is that several holders can be asked at once, and
what a requester submits is one round over many sites. So the inference runner
stops at the capability, and ``app.views.federated`` composes one runner per
selected asset and takes the round from there. Nothing else about it changes —
each site's capability still comes from that site's own policy.
"""

import logging

import requests

from . import pdo_runner, registry_client, session_keys
from .did_utils import parse_did
from .views._streaming import SkipStep

logger = logging.getLogger(__name__)


def guardian_endpoint(metadata):
    """The base URL of the guardian standing in front of an asset."""
    host = metadata.get("guardian_url", "")
    port = metadata.get("guardian_port", "")
    if not host or not port:
        raise ValueError("This asset has no guardian recorded.")
    return f"http://{host}:{port}"


def guardian_type_of(metadata):
    """The guardian type an asset was registered with.

    Assets registered before guardian types existed carry no ``guardian_type`` and
    are all download guardians, so that is the fallback.
    """
    return metadata.get("guardian_type") or "download"


def fetch_public_asset(asset_did):
    """Read an asset that is served in the clear, by its DID.

    Resolving DID -> registry -> guardian URL is what makes a public asset usable
    as a reference: anything that needs the bytes (a script, for instance) can name
    the asset and fetch it without any capability.
    """
    asset = registry_client.get_asset_by_did(asset_did)
    metadata = (asset or {}).get("metadata", {}) or {}
    if guardian_type_of(metadata) != "public":
        raise ValueError(f"Asset {asset_did} is not served by a public guardian.")

    resp = requests.get(f"{guardian_endpoint(metadata)}/data", timeout=30)
    resp.raise_for_status()
    return resp.text


class GuardianActionRunner:
    """Base class for the flow that uses an asset behind one kind of guardian."""

    # the guardian type this runner serves
    name = ""
    # what the button in the Use form says
    label = ""
    # whether the flow goes through the asset's policy agent at all
    needs_policy = True
    # whether the Use form must collect a wallet for each of the policy's roles
    needs_wallets = True
    # how the UI should render the result: "data" (text) or "metrics" (JSON)
    result_kind = "data"
    # whether this asset is used as one site of a federated round rather than on
    # its own. A federated asset has no Use button on the asset list; it is
    # selected, alongside others, from the Federated page.
    federated = False

    def __init__(self, *, user_name, asset_did, metadata, wallets=None, params=None):
        self.user_name = user_name
        self.asset_did = asset_did
        self.metadata = metadata or {}
        self.params = params or {}
        self.wallets = dict(wallets or {})

        self.guardian = guardian_endpoint(self.metadata)

        self.token_id = None
        if self.needs_policy:
            token_did = self.metadata.get("policy_contract", "")
            if not token_did:
                raise ValueError(
                    "Asset has not been exposed (no policy_contract in registry)."
                )
            self.token_id, _ = parse_did(token_did)

        if self.needs_wallets and not self.wallets:
            raise ValueError("A wallet is required for each role to use this asset.")

    # -----------------------------------------------------------------
    def steps(self):
        """Return the ``(step_id, label, fn)`` triples this flow runs."""
        raise NotImplementedError

    def result(self, ctx):
        """Return the terminal payload the UI renders, given the flow's context."""
        raise NotImplementedError

    def run(self):
        """Run every step in order and return the result.

        The plain (non-streaming) path; the streaming views hand ``steps()``
        straight to ``stream_steps`` instead.
        """
        ctx = {}
        for step_id, _, fn in self.steps():
            try:
                outcome = fn(ctx)
            except SkipStep as e:
                logger.info("step %r skipped: %s", step_id, e)
                continue
            if isinstance(outcome, dict):
                ctx.update(outcome)
        return self.result(ctx)

    # -----------------------------------------------------------------
    # shared steps
    # -----------------------------------------------------------------
    def _ensure_credential(self, ctx):
        """Obtain session-key credentials for whichever roles the policy wants them."""
        roles = pdo_runner.ensure_public_key_credential(
            self.wallets,
            self.token_id,
            self.user_name,
            lambda wallet_id: session_keys.keys_dir(self.user_name, wallet_id),
        )
        if not roles:
            raise SkipStep("not required or already present")
        return {"detail": f"obtained for: {', '.join(roles)}"}

    @property
    def _credential_step(self):
        return ("credential", "Checking credential requirements", self._ensure_credential)


class PublicGuardianActionRunner(GuardianActionRunner):
    """Read an asset that is published in the clear.

    No policy, no capability, no wallet — just the URL. It is here to show, next to
    the other two, what the absence of a guardian looks like, and to give scripts
    and other referenced artifacts a place to live where anyone can fetch them.
    """

    name = "public"
    label = "Fetch Data"
    needs_policy = False
    needs_wallets = False
    result_kind = "data"

    def steps(self):
        def fetch(ctx):
            ctx["data"] = fetch_public_asset(self.asset_did)
            return {"detail": f"{len(ctx['data'])} bytes, unauthenticated"}

        return [("fetch", "Fetching the data from the open server", fetch)]

    def result(self, ctx):
        return {"data": ctx.get("data", "")}


class DownloadGuardianActionRunner(GuardianActionRunner):
    """Download an asset encrypted to the requester's own session key.

    The capability the policy issues carries that key; the guardian encrypts the
    file to it, so only this requester can open what comes back.
    """

    name = "download"
    label = "Request Download"
    result_kind = "data"

    def steps(self):
        def download(ctx):
            output_path, _ = pdo_runner.use_asset(
                wallet_ids=self.wallets,
                token_id=self.token_id,
                guardian_url_port=self.guardian,
                user_name=self.user_name,
            )
            ctx["output_path"] = output_path

        def decrypt(ctx):
            wallet_id = self.wallets.get("User") or next(iter(self.wallets.values()))
            ctx["data"] = session_keys.decrypt_download(
                self.user_name, wallet_id, ctx["output_path"]
            )

        return [
            self._credential_step,
            ("download", "Requesting and downloading the data", download),
            ("decrypt", "Decrypting with your session key", decrypt),
        ]

    def result(self, ctx):
        return {"data": ctx.get("data", "")}


class InferenceGuardianActionRunner(GuardianActionRunner):
    """Mint the capability that lets one site run an approved script in place.

    The script is itself an asset behind a public guardian, and the identity chosen
    for the ``Script`` role *is* that asset. One choice therefore settles two
    things: the credentials describing the code (its digest, who owns it) are
    presented from it, and its DID resolves through the registry to the public
    guardian the script itself can be fetched from.

    The capability the policy issues carries the approved digest and is redeemable
    only at this asset's own guardian. It travels to the FL server and then to the
    FL client beside that guardian, which measures the script it actually received
    and presents that measurement when it redeems the capability. Approval and
    running code are checked against each other at the moment the data is released,
    not before.

    This runner stops there, because that is where one site's part ends: the
    script, the round, and the metrics belong to the federated flow that is asking
    several sites at once (see ``app.views.federated``). What that flow gets back
    from here is a capability and nothing else.
    """

    name = "inference"
    label = "Request Inference"
    result_kind = "capability"
    federated = True

    # The role whose identity is the script. Policies name it; see policy_cards/FL.
    SCRIPT_ROLE = "Script"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Checked here rather than left to the policy so the failure names the
        # missing choice instead of arriving as a denied evaluation. The federated
        # flow reads the same role to find the script it fetches for the round.
        if not self.wallets.get(self.SCRIPT_ROLE):
            raise ValueError(
                f"A script must be chosen for the '{self.SCRIPT_ROLE}' role to run "
                "inference."
            )

    def steps(self):
        def capability(ctx):
            cap, _ = pdo_runner.create_capability(
                wallet_ids=self.wallets,
                token_id=self.token_id,
                user_name=self.user_name,
            )
            ctx["capability"] = cap
            return {"detail": "issued by this site's own policy"}

        return [
            self._credential_step,
            ("capability", "Creating the inference capability", capability),
        ]

    def result(self, ctx):
        return {"capability": ctx.get("capability")}

    def mint_capability(self):
        """Run this site's half and return the capability, or raise.

        The federated flow reports one event per *site* rather than per step — a
        round over four hospitals showing twelve steps would bury which of them
        said no — so it runs the steps through here and reports the outcome.
        """
        return self.run()["capability"]


RUNNERS = {
    runner.name: runner
    for runner in (
        PublicGuardianActionRunner,
        DownloadGuardianActionRunner,
        InferenceGuardianActionRunner,
    )
}


def get_runner_class(guardian_type):
    """Return the runner class for a guardian type, or raise ``ValueError``."""
    try:
        return RUNNERS[guardian_type]
    except KeyError:
        raise ValueError(f"unknown guardian type: {guardian_type!r}")


def build_runner(*, user_name, asset_did, metadata, wallets=None, params=None):
    """Build the runner for whatever guardian stands in front of an asset."""
    runner_class = get_runner_class(guardian_type_of(metadata))
    return runner_class(
        user_name=user_name,
        asset_did=asset_did,
        metadata=metadata,
        wallets=wallets,
        params=params,
    )
