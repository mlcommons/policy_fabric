"""The federated page: run one script across several sites at once.

An asset behind an inference guardian is never used on its own. The reason to
leave data where it is, is that several holders can then be asked the same
question without any of them handing anything over — so the unit of work here is a
*round*: one script, several sites, one set of numbers back.

Three things have to line up for that, and this module is where they meet.

**Who is out there.** The sites are discovered from an FL server, not from the
asset registry: the registry knows which assets exist, but only the FL server
knows which of them currently have a client connected and ready to run. Each FL
client announces the DID of the asset it holds, so the two lists join on the DID —
the FL server says *a client holding this DID is up*, the registry says *this DID
is called `hospital_a_cohort` and sits behind a guardian at this address*. An
announced DID the registry has never heard of is shown as it is, unresolved,
rather than dropped; it is a real site, just not one this registry knows.

**What each site will allow.** Nothing about a round is decided centrally. Every
selected asset's own policy is asked separately, and each answers with a
capability minted for its own guardian — or refuses. A refusal removes that site
from the round and is reported; it does not stop the others. That is the honest
federated behaviour: the point of per-site policy is that one site saying no is a
fact about that site.

**Which capability is whose.** The capabilities are handed to the FL server
together, each tagged with the DID of the asset it was minted for, and the server
gives each client the one matching the DID that client announced. Nothing else
would work: a capability is bound to one guardian and is refused at every other,
so an untagged pile of them could only be handed out by guessing.
"""

import json
import logging
import time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from .. import (
    action_runners,
    fl_client,
    fl_launcher,
    ledger_client,
    pdo_runner,
    registry_client,
    service_launcher,
)
from ..did_utils import make_did, parse_did
from ..models import AppConfig
from ._helpers import BaseView, JsonView, ValidationError
from ._streaming import make_event, stream_events, stream_steps

logger = logging.getLogger(__name__)

# A round is only as fast as its slowest site, and a site's work starts with its
# FL client noticing the job on its next poll.
ROUND_TIMEOUT = 300
ROUND_POLL_INTERVAL = 2

# Progress steps that are about one site rather than about the round. They are
# numbered rather than named after the asset: a step id ends up in a CSS
# attribute selector in the browser, and a DID is not a thing to put in one.
PER_SITE_STEPS = ("site:", "run:")


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _federated_assets_by_did():
    """Every registered asset that is a federated site, keyed by DID."""
    assets = {}
    for asset in registry_client.list_assets() or []:
        metadata = asset.get("metadata") or {}
        runner_class = action_runners.RUNNERS.get(
            action_runners.guardian_type_of(metadata)
        )
        if not (runner_class and runner_class.federated):
            continue
        assets[asset["did"]] = asset
    return assets


def _site_rows(server_url):
    """Join what an FL server reports against what the asset registry knows.

    One row per connected client. ``known`` says whether this registry has an
    asset under that DID — an unknown one is still a site, and is shown as such,
    because a federation is not required to share one registry.
    """
    clients = fl_client.list_clients(server_url)
    registered = _federated_assets_by_did()

    rows = []
    for client in clients:
        did = client.get("asset_did") or ""
        asset = registered.get(did)
        metadata = (asset or {}).get("metadata") or {}
        rows.append(
            {
                "asset_did": did,
                "client_id": client.get("client_id") or "",
                "online": bool(client.get("online")),
                "seconds_since_seen": client.get("seconds_since_seen"),
                "jobs_claimed": client.get("jobs_claimed") or 0,
                "known": asset is not None,
                "name": (asset or {}).get("name")
                or client.get("asset_name")
                or "(not in this registry)",
                "guardian": (
                    f"{metadata.get('guardian_url', '')}:{metadata.get('guardian_port', '')}"
                    if metadata.get("guardian_url")
                    else ""
                ),
                # A site with no policy attached has nothing to ask, so it cannot
                # take part however healthy its client is.
                "exposed": bool(metadata.get("policy_contract")),
            }
        )

    rows.sort(key=lambda r: (not r["online"], not r["exposed"], r["name"].lower()))
    return rows


def _selectable(row):
    """Whether a site can be included in a round right now."""
    return row["online"] and row["known"] and row["exposed"]


class FederatedPageView(BaseView):
    """GET-only: the page. The site list is fetched by JS against a chosen server."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key

        # The identities a role can be presented from: the requester's own
        # wallets, and the script assets whose identities hold the credentials
        # about the code. Same two kinds the single-asset Use modal offers.
        from .assets import _user_wallet_cards  # local: avoids a circular import

        wallets = _user_wallet_cards(user_name)

        # Only locally owned scripts are offered: presenting a role from an
        # identity means invoking that identity's contract.
        scripts = []
        try:
            owned = set(ledger_client.list_signature_authority_ids(user_name))
            for asset in registry_client.list_assets() or []:
                metadata = asset.get("metadata") or {}
                if action_runners.guardian_type_of(metadata) != "public":
                    continue
                contract_id, _ = parse_did(asset["did"])
                if contract_id not in owned:
                    continue
                scripts.append(
                    {
                        "contract_id": contract_id,
                        "name": asset["name"],
                        "did": asset["did"],
                    }
                )
        except Exception:
            logger.exception("Failed to list script assets")

        return render(
            request,
            "federated/list.html",
            {
                "default_server_url": fl_client.default_server_url(),
                "wallets": wallets,
                "script_assets": scripts,
            },
        )


class FederatedSitesEndpoint(JsonView):
    """POST {server_url} — the sites connected to an FL server, joined with the
    asset registry."""

    def handle(self, request, data, **kwargs):
        server_url = data.get("server_url") or fl_client.default_server_url()
        try:
            server_url = fl_client.normalize_url(server_url)
        except ValueError as e:
            raise ValidationError(str(e))

        try:
            server_info = fl_client.info(server_url)
        except Exception as e:
            raise ValidationError(f"no FL server answering at {server_url}: {e}")

        try:
            rows = _site_rows(server_url)
        except Exception as e:
            logger.exception("Failed to list FL sites")
            raise ValidationError(f"failed to list the sites at {server_url}: {e}")

        for row in rows:
            row["selectable"] = _selectable(row)

        return {
            "ok": True,
            "server_url": server_url,
            "server_info": server_info,
            "sites": rows,
        }


class FederatedStartServerStreamView(BaseView):
    """POST {} — start an FL server on this host and wait for it to answer.

    Deliberately not part of using an asset. A round is submitted to a server that
    is already there, and this exists only for the case where the address this
    deployment is pointed at has nothing on it — the Federated page offers it after
    a failed connection, and never otherwise.

    When the webapp is containerized the command is handed to the host-side
    watcher rather than run here, which is how a container starts a sibling
    container without a Docker socket of its own (see ``app.service_launcher``).
    """

    http_method_names = ["post"]

    def post(self, request):
        def start(ctx):
            ctx["server_url"] = fl_launcher.deploy()
            where = "by the host" if settings.CONTAINERIZED_DEPLOYMENT else "here"
            return {"detail": f"{ctx['server_url']}, started {where}"}

        def wait(ctx):
            service_launcher.wait_until_healthy(ctx["server_url"])

        return stream_steps(
            [
                ("start", "Starting an FL server", start),
                ("health", "Waiting for it to answer", wait),
            ],
            complete=lambda ctx: {
                "server_url": ctx["server_url"],
                "message": f"FL server running at {ctx['server_url']}.",
            },
        )


class FederatedRolesEndpoint(JsonView):
    """POST {asset_dids: [...]} — the union of roles the selected sites ask for.

    Each site's policy declares its own roles, so a round over several of them has
    to collect every role any of them wants. A site that wants fewer simply
    ignores what it was not asked for.
    """

    def handle(self, request, data, **kwargs):
        asset_dids = data.get("asset_dids")
        if not isinstance(asset_dids, list) or not asset_dids:
            raise ValidationError("select at least one site")

        user_name = AppConfig.get_instance().public_key

        roles = {}
        problems = []
        for asset_did in asset_dids:
            try:
                asset = registry_client.get_asset_by_did(asset_did) or {}
            except Exception as e:
                problems.append(f"{asset_did}: not in the asset registry ({e})")
                continue
            name = asset.get("name") or asset_did
            metadata = asset.get("metadata") or {}
            token_did = metadata.get("policy_contract", "")
            if not token_did:
                problems.append(f"{name}: not exposed yet")
                continue
            try:
                token_id, _ = parse_did(token_did)
                requirements = pdo_runner.get_policy_requirements(token_id, user_name)
            except Exception as e:
                logger.exception("Failed to read policy requirements for %s", asset_did)
                problems.append(f"{name}: {e}")
                continue
            for role, types in (requirements or {}).items():
                roles.setdefault(role, set()).update(types)

        if problems and not roles:
            raise ValidationError("; ".join(problems))

        return {
            "ok": True,
            "roles": [
                {"role": role, "credential_types": sorted(types)}
                for role, types in sorted(roles.items())
            ],
            "problems": problems,
        }


class FederatedRunStreamView(BaseView):
    """POST {server_url, asset_dids, wallets} — run one federated round, streaming.

    The steps are emitted by hand rather than through ``stream_steps`` because the
    shape of this flow depends on what the requester selected: one capability step
    per site, then the round. A site the policy refuses is reported as an error on
    its own step and dropped; the round goes ahead with whoever is left.
    """

    http_method_names = ["post"]

    def post(self, request):
        data = _json_body(request)
        user_name = AppConfig.get_instance().public_key

        try:
            server_url = fl_client.normalize_url(
                data.get("server_url") or fl_client.default_server_url()
            )
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        asset_dids = data.get("asset_dids")
        if not isinstance(asset_dids, list) or not asset_dids:
            return JsonResponse({"error": "select at least one site"}, status=400)

        from .assets import _clean_wallets  # local: avoids a circular import

        try:
            wallets = _clean_wallets(data, user_name)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        script_role = action_runners.InferenceGuardianActionRunner.SCRIPT_ROLE
        script_contract = wallets.get(script_role)
        if not script_contract:
            return JsonResponse(
                {"error": f"a script must be chosen for the '{script_role}' role"},
                status=400,
            )
        script_did = make_did(script_contract)

        state = {}
        return stream_events(
            self._events(
                user_name=user_name,
                server_url=server_url,
                asset_dids=asset_dids,
                wallets=wallets,
                script_did=script_did,
                state=state,
            ),
            complete=lambda: {
                "result": state.get("round", {}),
                "result_kind": "round",
                "message": "Federated round completed.",
            },
            # A site refusing, or failing at its own guardian, is a result about
            # that site: it belongs in the round's report, next to what everyone
            # else returned, rather than collapsing the whole flow into an error
            # with nothing to show. Only the steps that are about the round itself
            # -- the script, the submission, the wait -- can end it.
            fatal=lambda event: not event["step"].startswith(PER_SITE_STEPS),
        )

    # -----------------------------------------------------------------
    def _events(self, *, user_name, server_url, asset_dids, wallets, script_did, state):
        """Yield one progress event per transition, in the order they happen."""
        # ---- the script: one piece of code, for every site in the round -----
        step = "script"
        label = "Fetching the script from its public guardian"
        yield make_event(step, "start", label)
        try:
            script = action_runners.fetch_public_asset(script_did)
        except Exception as e:
            logger.exception("Failed to fetch the script")
            yield make_event(step, "error", label, str(e))
            return
        yield make_event(step, "done", label, f"{len(script)} bytes from {script_did}")

        # ---- one capability per site, each from that site's own policy ------
        # Asked one at a time and independently. Nothing about this round is
        # decided centrally: each owner's policy reads the same evidence and
        # reaches its own verdict, and a refusal here removes that site and
        # nothing else.
        participants = []
        refused = []
        names = {asset_did: self._name_of(asset_did) for asset_did in asset_dids}
        for index, asset_did in enumerate(asset_dids):
            name = names[asset_did]
            step = f"site:{index}"
            label = f"Asking {name} for a capability"
            # Announced before the asking, not after: a policy deliberating is the
            # slowest and most interesting moment in the flow, and it should be
            # visible while it happens rather than only in its verdict.
            yield make_event(step, "start", label)
            outcome = self._mint(user_name, asset_did, wallets)
            if outcome["ok"]:
                participants.append(
                    {"asset_did": asset_did, "capability": outcome["capability"]}
                )
                yield make_event(step, "done", label, outcome["detail"])
            else:
                refused.append({"asset_did": asset_did, "name": name, "error": outcome["detail"]})
                yield make_event(step, "error", label, outcome["detail"])

        if not participants:
            yield make_event(
                "round",
                "error",
                "Submitting the round to the FL server",
                "no site issued a capability, so there is no round to run",
            )
            return

        # ---- the round ------------------------------------------------------
        step, label = "round", "Submitting the round to the FL server"
        yield make_event(step, "start", label)
        try:
            record = fl_client.submit_round(
                server_url,
                script,
                participants,
                script_name=script_did,
                round_name=f"{len(participants)}-site round",
            )
        except Exception as e:
            logger.exception("Failed to submit the round")
            yield make_event(step, "error", label, str(e))
            return
        round_id = record["round_id"]
        yield make_event(
            step, "done", label, f"round {round_id} over {len(participants)} site(s)"
        )

        # ---- waiting: one event per site, as each of them reports -----------
        # Polled here rather than through ``fl_client.wait_for_round`` so that a
        # site finishing can be shown when it finishes. In a round over several
        # hospitals, "two of four have reported" is the interesting state, and a
        # single blocking wait would never show it.
        running = {p["asset_did"]: index for index, p in enumerate(participants)}
        for asset_did, index in running.items():
            yield make_event(
                f"run:{index}", "start", f"Waiting for {names[asset_did]} to report"
            )

        seen = set()
        deadline = time.monotonic() + ROUND_TIMEOUT
        record = None
        while time.monotonic() < deadline:
            try:
                record = fl_client.get_round(server_url, round_id)
            except Exception as e:
                logger.warning("could not poll round %s (%s); retrying", round_id, e)
                time.sleep(ROUND_POLL_INTERVAL)
                continue

            for participant in record["participants"]:
                asset_did = participant["asset_did"]
                status = participant.get("status")
                if asset_did in seen or status not in fl_client.TERMINAL_STATUSES:
                    continue
                seen.add(asset_did)
                step = f"run:{running[asset_did]}"
                label = f"Waiting for {names.get(asset_did, asset_did)} to report"
                if status == "complete":
                    metrics = participant.get("metrics") or {}
                    yield make_event(
                        step, "done", label, f"{metrics.get('samples', '?')} samples"
                    )
                else:
                    yield make_event(
                        step,
                        "error",
                        label,
                        participant.get("error") or "the site reported a failure",
                    )

            if record.get("status") in fl_client.TERMINAL_STATUSES:
                break
            time.sleep(ROUND_POLL_INTERVAL)
        else:
            still = [names[did] for did in running if did not in seen]
            yield make_event(
                "aggregate",
                "error",
                "Aggregating what the sites reported",
                f"round {round_id} did not finish within {ROUND_TIMEOUT}s; "
                f"still waiting on {', '.join(still)}",
            )
            return

        step, label = "aggregate", "Aggregating what the sites reported"
        yield make_event(step, "start", label)
        ran = sum(1 for p in record["participants"] if p.get("status") == "complete")
        state["round"] = self._describe(record, refused, server_url, names)
        yield make_event(
            step, "done", label, f"{ran} of {len(participants)} site(s) ran it"
        )

    # -----------------------------------------------------------------
    def _name_of(self, asset_did):
        """This registry's name for an asset, or its DID if it has none."""
        try:
            return (registry_client.get_asset_by_did(asset_did) or {}).get(
                "name"
            ) or asset_did
        except Exception:
            return asset_did

    def _mint(self, user_name, asset_did, wallets):
        """Ask one site's policy for a capability. Never raises.

        Returns ``{"ok", "capability"|"detail"}``. A refusal is a result, not an
        exception: the round carries on without this site, and what the policy
        said is what the requester is shown.
        """
        try:
            asset = registry_client.get_asset_by_did(asset_did) or {}
            runner = action_runners.build_runner(
                user_name=user_name,
                asset_did=asset_did,
                metadata=asset.get("metadata") or {},
                wallets=wallets,
            )
            if not runner.federated:
                return {
                    "ok": False,
                    "detail": "this asset is not behind an inference guardian",
                }
            capability = runner.mint_capability()
        except Exception as e:
            logger.exception("Site %s did not issue a capability", asset_did)
            return {"ok": False, "detail": str(e)}
        return {"ok": True, "capability": capability, "detail": "issued"}

    # -----------------------------------------------------------------
    def _describe(self, record, refused, server_url, names):
        """The round as the page renders it: names in, DIDs kept for reference."""
        sites = [
            {**p, "name": names.get(p["asset_did"], p["asset_did"])}
            for p in record["participants"]
        ]
        return {
            "round_id": record["round_id"],
            "status": record["status"],
            "server_url": server_url,
            "aggregate": record.get("aggregate"),
            "sites": sites,
            "refused": refused,
        }
