import json
import logging
import socket

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from .. import (
    action_runners,
    guardian_launcher,
    guardian_registry,
    ledger_client,
    naming,
    pdo_runner,
    readiness,
    registry_client,
    schemas,
    trust,
)
from ..did_utils import make_did, parse_did
from ..models import AppConfig
from ..url_safe_id import decode_cid, encode_cid
from ._helpers import (
    BaseView,
    JsonView,
    ValidationError,
    redirect_with_msg,
    require,
)
from ._streaming import SkipStep, stream_steps

logger = logging.getLogger(__name__)


def _json_body(request):
    """Parse a JSON request body into a dict (empty dict if absent/invalid)."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _guardian_url_port(host, port):
    """Compose the canonical guardian URL the rego token contract stores."""
    return f"http://{host}:{port}"


FEDERATED_ONLY = (
    "This asset is one site of a federated round, not something to run on its "
    "own. Select it, with the others you want, on the Federated page."
)


def _reject_federated(metadata):
    """Raise ``ValidationError`` if this asset is only usable federated.

    Both single-asset Use endpoints go through here rather than quietly doing half
    of a federated round: an inference capability is minted for one guardian and
    then has to reach an FL server with the rest of its round, which this path
    knows nothing about.
    """
    runner_class = action_runners.RUNNERS.get(
        action_runners.guardian_type_of(metadata)
    )
    if runner_class and runner_class.federated:
        raise ValidationError(FEDERATED_ONLY)


def _offerable_guardians():
    """The guardians the registration form may offer.

    A guardian is offerable when it can be both launched and used: its folder
    supplies a manifest, and ``app.action_runners`` supplies a runner keyed by the
    same type. Registering an asset behind a guardian nobody can drive would only
    produce an asset that cannot be used.
    """
    return [
        m for m in guardian_registry.manifests() if m.type in action_runners.RUNNERS
    ]


def _guardian_options(form=None):
    """The guardian choices the registration form offers, with the current picks.

    ``form`` is the submitted data on a re-render, so a failed registration comes
    back with the owner's selections intact.
    """
    form = form or {}
    guardians = _offerable_guardians()
    default_type = settings.DEFAULT_GUARDIAN_TYPE
    if not any(m.type == default_type for m in guardians):
        default_type = guardians[0].type if guardians else ""
    return {
        "guardians": guardians,
        "serve_on_choices": settings.SERVE_ON_CHOICES,
        "guardian_type": form.get("guardian_type") or default_type,
        "serve_on": form.get("serve_on") or settings.DEFAULT_SERVE_ON,
        "port": form.get("port") or settings.GUARDIAN_PORT,
    }


def _clean_guardian_choice(data):
    """Validate the guardian fields of a registration request.

    Returns ``(guardian_type, serve_on, port)``. Raises ``ValueError`` with a
    message meant for the owner.
    """
    guardian_type = (data.get("guardian_type") or settings.DEFAULT_GUARDIAN_TYPE).strip()
    serve_on = (data.get("serve_on") or settings.DEFAULT_SERVE_ON).strip()
    port = str(data.get("port") or settings.GUARDIAN_PORT).strip()

    offerable = {m.type for m in _offerable_guardians()}
    if guardian_type not in offerable:
        raise ValueError(f"Unknown guardian type: {guardian_type}")
    if serve_on not in settings.SERVE_ON_CHOICES:
        raise ValueError(f"Unknown serve_on choice: {serve_on}")
    if not port.isdigit() or not (1 <= int(port) <= 65535):
        raise ValueError(f"Port must be a number between 1 and 65535: {port}")

    return guardian_type, serve_on, port


def _published_ports(guardian_type, port):
    """The host ports a guardian of ``guardian_type`` on ``port`` publishes: its
    own, and the storage service's beside it for the guardians that run one."""
    ports = [str(port)]
    if "storage_port" in guardian_registry.get(guardian_type).options.values():
        ports.append(str(guardian_launcher.storage_port(port)))
    return ports


def _registered_on_port(host, port):
    """The name of the registered asset whose guardian publishes ``port`` on
    ``host``, or ``None``."""
    try:
        assets = registry_client.list_assets() or []
    except Exception:
        return None
    for asset in assets:
        metadata = asset.get("metadata") or {}
        if metadata.get("guardian_url") != host:
            continue
        try:
            published = _published_ports(
                action_runners.guardian_type_of(metadata), metadata.get("guardian_port")
            )
        except (KeyError, TypeError, ValueError):
            continue
        if str(port) in published:
            return asset.get("name")
    return None


def _check_ports_free(guardian_type, serve_on, port):
    """Raise ``ValueError`` if a port the new guardian would publish is taken.

    Nothing downstream notices on its own. An inference guardian's run.sh replaces
    whatever containers are already on its port -- another asset's guardian and
    FL client with them -- and a public guardian that cannot bind dies while the
    one already there keeps answering. Either way the health check is satisfied by
    whatever was listening, and the new asset is registered in front of somebody
    else's guardian. So the ports are probed first, at the address the guardian
    will be advertised on.
    """
    _, host = guardian_launcher.resolve_serve_on(serve_on)
    ports = _published_ports(guardian_type, port)

    for candidate in ports:
        try:
            with socket.create_connection((host, int(candidate)), timeout=1):
                pass
        except OSError:
            continue
        holder = _registered_on_port(host, candidate)
        by = f" by the guardian of '{holder}'" if holder else ""
        raise ValueError(
            f"Port {candidate} on {host} is already in use{by}. Choose another "
            f"port: this guardian needs {' and '.join(ports)} free."
        )


def _clean_wallets(data, user_name):
    """Pull the per-role wallet choices out of a use request.

    ``{"wallets": {role: contract_id}}`` is the general form. A bare
    ``{"wallet_id": ...}`` is accepted as shorthand for the ``User`` role, which is
    the only role a single-role policy has. Every named wallet must belong to the
    current identity.
    """
    wallets = data.get("wallets")
    if not isinstance(wallets, dict):
        wallet_id = (data.get("wallet_id") or "").strip()
        wallets = {"User": wallet_id} if wallet_id else {}

    cleaned = {}
    for role, contract_id in wallets.items():
        contract_id = (contract_id or "").strip()
        if not contract_id:
            raise ValidationError(f"no wallet chosen for the '{role}' role")
        if not ledger_client.user_owns_contract(user_name, contract_id):
            raise ValidationError(f"wallet not found: {contract_id}")
        cleaned[role] = contract_id
    return cleaned


def _token_and_policy(did, user_name):
    """The token and policy agent behind an exposed asset, or raise ValidationError."""
    try:
        metadata = registry_client.get_asset_by_did(did)["metadata"]
    except Exception as e:
        raise ValidationError(f"failed to look up asset in registry: {e}")
    if "policy_contract" not in metadata:
        raise ValidationError("Asset has no policy agent yet (expose it first).")
    token_id, _ = parse_did(metadata["policy_contract"])
    try:
        return token_id, pdo_runner.resolve_policy_id(token_id, user_name)
    except ValueError as e:
        raise ValidationError(str(e))


def _facts_needing_authorities(modules, templates):
    """The facts some module reads that an authority has to establish: all but
    the self-asserted ones, which the requester signs and the policy checks
    against their key."""
    facts = {t for m in modules for types in m["requirements"].values() for t in types}
    return sorted(f for f in facts if not templates[f]["self_asserted"])


def _short_id(contract_id, n=12):
    return contract_id[:n]


def _with_article(word):
    """``word`` with its indefinite article: "a public", "an inference"."""
    return f"{'an' if word and word[0].lower() in 'aeiou' else 'a'} {word}"


def _user_wallet_cards(user_name):
    """Wallet picker entries for the asset list / asset dashboard 'Use' modal.

    Mirrors ``views.wallets._user_wallet_ids`` but inlined to avoid a circular
    import. Wallets = identity.identity contracts (a disjoint ledger family
    from the signature_authority contracts asset identities use, so no
    asset-id subtraction is needed here).
    """
    ids = ledger_client.list_identity_ids(user_name)
    names = naming.get_names([make_did(cid) for cid in ids])
    return [{"contract_id": cid, "name": names[make_did(cid)]} for cid in ids]


def _require_user_asset(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's assets.

    Asset ownership = (a) the contract id is in the user's on-ledger
    contract list, and (b) the DID is registered in the asset registry.
    """
    if not ledger_client.user_owns_contract(user_name, contract_id):
        raise Http404(f"asset not found: {contract_id}")
    try:
        registry_client.get_asset_by_did(make_did(contract_id))
    except Exception:
        raise Http404(f"asset not registered: {contract_id}")


class AssetsListView(BaseView):
    """GET-only: list all assets in the registry, annotated with ownership."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        assets = []
        list_error = None
        try:
            assets = registry_client.list_assets() or []
            owned_ids = set(ledger_client.list_signature_authority_ids(user_name))
            for a in assets:
                cid, _ = parse_did(a["did"])
                metadata = a.get("metadata") or {}
                a["contract_id"] = cid
                a["cid_url"] = encode_cid(cid)
                a["is_local"] = cid in owned_ids
                # An asset can only be "used" once it is behind a guardian.
                a["has_guardian"] = bool(metadata.get("guardian_url"))
                # What the Use modal offers is decided by the guardian the owner
                # registered the asset with.
                guardian_type = action_runners.guardian_type_of(metadata)
                runner_class = action_runners.RUNNERS.get(guardian_type)
                a["guardian_type"] = guardian_type
                a["action_label"] = runner_class.label if runner_class else "Use"
                a["needs_wallets"] = bool(runner_class and runner_class.needs_wallets)
                # An asset behind an inference guardian is one site of a federated
                # round, never a thing to run on its own, so this page does not
                # offer to run it — the Federated page does, over several at once.
                a["federated"] = bool(runner_class and runner_class.federated)
        except Exception as e:
            logger.exception("Failed to fetch assets")
            list_error = str(e)

        wallets = _user_wallet_cards(user_name)
        # A role is presented from whichever identity holds that role's credentials.
        # For the requester that is one of their wallets; for a script it is the
        # script asset itself, whose identity contract holds the credentials about
        # it and whose DID resolves to the public guardian it can be fetched from.
        # Only locally owned ones are offered, since presenting from an identity
        # means invoking it.
        script_assets = [
            {"contract_id": a["contract_id"], "name": a["name"], "did": a["did"]}
            for a in assets
            if a.get("guardian_type") == "public" and a.get("is_local")
        ]
        return render(
            request,
            "assets/list.html",
            {
                "assets": assets,
                "wallets": wallets,
                "script_assets": script_assets,
                "list_error": list_error,
            },
        )


class AssetSetupView(BaseView):
    """GET: registration form. POST: deploy a guardian for the data and register
    the asset.

    Registering an asset does three things in this order: mint the identity
    contract that gives the asset its DID, start a guardian for the given data
    path (told that DID), and — once the guardian answers — record the asset in
    the registry.

    The DID has to come first because a guardian may need to say which asset it
    holds: an inference guardian announces exactly that to an FL server, and a site
    that cannot name what it is holding is a site no round can be addressed to. The
    registry entry still comes last, so an asset never appears without a working
    guardian behind it.
    """

    def get(self, request):
        return render(request, "assets/setup.html", _guardian_options())

    def _error(self, request, message):
        ctx = _guardian_options(request.POST)
        ctx.update({"form": request.POST, "error": message})
        return render(request, "assets/setup.html", ctx)

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        data_source = (request.POST.get("data_source") or "").strip()

        if not all([name, data_source]):
            return self._error(request, "All fields are required.")

        try:
            guardian_type, serve_on, port = _clean_guardian_choice(request.POST)
            _check_ports_free(guardian_type, serve_on, port)
        except ValueError as e:
            return self._error(request, str(e))

        config = AppConfig.get_instance()
        user_name = config.public_key

        try:
            contract_id = pdo_runner.create_asset_identity(name, user_name)
            did = make_did(contract_id)
        except Exception as e:
            logger.exception("Failed to create the asset contract")
            return self._error(request, f"Failed to create the asset contract: {e}")

        # Start the guardian, told which asset it is holding, and wait until it is
        # up; only then register the asset, so an asset never appears in the
        # registry without a working guardian.
        try:
            guardian_url, guardian_port = guardian_launcher.deploy_guardian(
                data_source,
                guardian_type=guardian_type,
                serve_on=serve_on,
                port=port,
                asset_did=did,
                asset_name=name,
            )
            guardian_launcher.wait_until_healthy(guardian_url, guardian_port)
        except Exception as e:
            logger.exception("Failed to deploy guardian")
            return self._error(request, f"Failed to deploy guardian: {e}")

        try:
            registry_asset = registry_client.register_asset(
                name=name,
                did=did,
                metadata={
                    "data_source": data_source,
                    "guardian_url": guardian_url,
                    "guardian_port": guardian_port,
                    "guardian_type": guardian_type,
                    "serve_on": serve_on,
                },
            )

            registry_pk = registry_asset["id"]
            asset_registry_url = (
                f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{registry_pk}/"
            )
            registry_client.update_asset_metadata(
                registry_pk, {"asset_registry_url": asset_registry_url}
            )

        except Exception as e:
            logger.exception("Failed to register asset")
            return self._error(request, f"Failed to register asset: {e}")

        return redirect_with_msg(
            "/",
            f'Asset "{name}" registered behind {_with_article(guardian_type)} guardian.',
            "success",
        )


class AssetDashboardView(BaseView):
    """GET-only: render the per-asset dashboard.

    Before the asset is exposed, the dashboard offers the Expose panel: the cards
    that can sit in front of this asset's guardian, a parameter form per card,
    and the authorities the owner accepts for each fact. Afterwards it shows the
    cards attached, the accepted authorities by name and kind (with a way to
    withdraw or add trust), and the policy data.
    """

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        try:
            asset = registry_client.get_asset_by_did(did) or {}
            registry_error = None
        except Exception as e:
            logger.exception("Failed to fetch asset from registry")
            asset, registry_error = {}, str(e)

        metadata = asset.get("metadata", {}) or {}
        guardian_url = metadata.get("guardian_url", "")
        guardian_port = metadata.get("guardian_port", "")
        guardian_deployed = bool(guardian_url and guardian_port)
        guardian_type = action_runners.guardian_type_of(metadata)
        runner_class = action_runners.RUNNERS.get(guardian_type)
        ctx = {
            "asset": {
                "contract_id": contract_id,
                "cid_url": cid_url,
                "did": did,
                "name": asset.get("name") or f"Asset {_short_id(contract_id)}",
            },
            "guardian_deployed": guardian_deployed,
            "guardian_type": guardian_type,
            "serve_on": metadata.get("serve_on", ""),
            "supports_policy": bool(runner_class and runner_class.needs_policy),
            "guardian_endpoint": (
                _guardian_url_port(guardian_url, guardian_port) if guardian_deployed else ""
            ),
            "has_policy": False,
            "registry_error": registry_error,
            "error": None,
        }

        if "policy_contract" in metadata:
            self._exposed(ctx, did, metadata, user_name)
        elif guardian_deployed and ctx["supports_policy"]:
            self._expose_panel(ctx, guardian_type)
        return render(request, "assets/dashboard.html", ctx)

    def _exposed(self, ctx, did, metadata, user_name):
        ctx["has_policy"] = True
        try:
            token_id, policy_id = _token_and_policy(did, user_name)
            requirements = pdo_runner.get_policy_requirements(token_id, user_name)
            trusted = pdo_runner.list_trusted_issuers(policy_id, user_name)
            policy_data = pdo_runner.get_policy_data(policy_id, user_name)
            templates = registry_client.credential_templates_by_type()
            modules = {t["name"]: t for t in registry_client.list_policy_templates()}
            directory = registry_client.list_authorities()
        except Exception as e:
            logger.exception("Failed to read the asset's policy")
            ctx["error"] = str(e)
            return

        names = {t: v["display_name"] for t, v in templates.items()}
        facts = _facts_needing_authorities([{"requirements": requirements}], templates)
        every_fact = {t for types in requirements.values() for t in types}
        ctx.update({
            "policy_contract_id": policy_id,
            "cards": [
                {
                    **card,
                    "parameters_schema": modules[card["name"]]["parameters_schema"],
                    "values": policy_data[card["name"]],
                }
                for card in metadata["cards"]
            ],
            "delivery": modules[metadata["delivery"]]["title"],
            "trust_rows": trust.panel(facts, trusted, directory, names),
            "self_asserted": [names[t] for t in sorted(every_fact - set(facts))],
        })

    def _expose_panel(self, ctx, guardian_type):
        try:
            cards = registry_client.policy_templates_for(guardian_type, "policy")
            delivery = registry_client.delivery_template(guardian_type)
            credentials = registry_client.list_credential_templates()
            ctx["expose"] = {
                "cards": [
                    {k: c[k] for k in ("id", "name", "code", "title", "rule", "requirements",
                                       "parameters_schema", "defaults", "readme", "rego_source")}
                    for c in cards
                ],
                "delivery": {k: delivery[k] for k in ("name", "title", "rule", "requirements")},
                "facts": {
                    t["template_type"]: {
                        "name": t["display_name"],
                        "meaning": t["meaning"],
                        "self_asserted": t["self_asserted"],
                    }
                    for t in credentials
                },
                "authorities": [trust.describe(a) for a in registry_client.list_authorities()],
                "trust_lists": registry_client.list_trust_lists(),
            }
        except Exception as e:
            logger.exception("Failed to load the expose panel")
            ctx["error"] = str(e)


def _expose_steps(contract_id, did, user_name, payload):
    """The steps that expose an asset: the chosen cards and the delivery module of
    its guardian in one policy agent, each card's parameters under its own module
    id, and the authorities accepted for each fact.

    ``payload`` is ``{cards: [template id, ...], parameters: {template id: {...}},
    authorities: {fact: [authority DID, ...]}}``, with parameters for every card
    and authorities for every fact an authority has to establish.
    """
    for key, kind in (("cards", list), ("parameters", dict), ("authorities", dict)):
        if not isinstance(payload.get(key), kind):
            raise ValidationError(f"'{key}' must be a {kind.__name__}")
    card_ids = [str(i) for i in payload["cards"]]
    parameters, choices = payload["parameters"], payload["authorities"]
    if not card_ids:
        raise ValidationError("Select at least one policy.")
    if set(parameters) != set(card_ids):
        raise ValidationError("'parameters' must hold the parameters of every selected policy")

    def load(ctx):
        asset = registry_client.get_asset_by_did(did)
        meta = asset["metadata"]
        host, port = meta["guardian_url"], meta["guardian_port"]
        if not host or not port:
            raise ValueError("Guardian URL/port missing on this asset.")

        cards = [registry_client.get_policy_template(i) for i in card_ids]
        delivery = registry_client.delivery_template(action_runners.guardian_type_of(meta))
        # every module reads its own slice; the delivery module has no parameters
        policy_data, problems = {delivery["name"]: {}}, []
        for card in cards:
            values = parameters[str(card["id"])]
            for problem in schemas.errors(values, card["parameters_schema"]):
                problems.append(f"{card['code']} {problem}")
            policy_data[card["name"]] = values
        if problems:
            raise ValueError("Parameters do not fit: " + "; ".join(problems))

        facts = _facts_needing_authorities(cards + [delivery], registry_client.credential_templates_by_type())
        if set(choices) != set(facts):
            raise ValueError("'authorities' must name the accepted authorities of: " + ", ".join(facts))
        unaccepted = [f for f in facts if not choices[f]]
        if unaccepted:
            raise ValueError("Accept at least one authority for: " + ", ".join(unaccepted))

        ctx.update({
            "modules": [[c["name"], c["rego_source"]] for c in cards + [delivery]],
            "policy_data": policy_data,
            "cards": [{"name": c["name"], "code": c["code"], "title": c["title"], "rule": c["rule"]} for c in cards],
            "delivery": delivery["name"],
            "guardian": _guardian_url_port(host, port),
            "asset_name": asset["name"],
            "registrations": trust.registrations({f: choices[f] for f in facts}),
        })
        return {"detail": f"{len(cards)} polic{'y' if len(cards) == 1 else 'ies'} and the {delivery['title'].lower()}"}

    def create_policy(ctx):
        result = pdo_runner.create_asset_policy(
            f"Policy for {ctx['asset_name']}", ctx["guardian"], user_name, ctx["modules"]
        )
        ctx["policy_id"] = result["policy_contract_id"]
        ctx["token_id"] = result["token_contract_id"]

    def set_data(ctx):
        pdo_runner.set_policy_data(ctx["policy_id"], ctx["policy_data"], user_name)

    def accept_authorities(ctx):
        for issuer_id, path, facts in ctx["registrations"]:
            pdo_runner.register_trusted_issuer(
                ctx["policy_id"], issuer_id, user_name, path=path, credential_types=facts
            )
        return {"detail": f"{len(ctx['registrations'])} authorit{'y' if len(ctx['registrations']) == 1 else 'ies'}"}

    def update_registry(ctx):
        registry_client.update_asset_metadata_by_did(did, {
            "policy_contract": make_did(ctx["token_id"]),
            "policy_data": ctx["policy_data"],
            "cards": ctx["cards"],
            "delivery": ctx["delivery"],
        })

    return [
        ("load", "Loading the selected policies", load),
        ("policy", "Creating the policy and token contracts", create_policy),
        ("data", "Setting each policy's parameters", set_data),
        ("authorities", "Accepting the chosen authorities", accept_authorities),
        ("registry", "Updating the asset registry", update_registry),
    ]


def expose(contract_id, did, user_name, payload):
    """Expose an asset in one go; the plain counterpart of the streamed flow."""
    ctx = {}
    for _, _, fn in _expose_steps(contract_id, did, user_name, payload):
        try:
            fn(ctx)
        except SkipStep:
            continue
    return ctx


class AssetExposeView(BaseView):
    """POST: the plain-form fallback of :class:`AssetExposeStreamView`, with the
    same JSON payload in a ``payload`` field."""

    def get(self, request, cid_url):
        return redirect("asset_dashboard", cid_url=cid_url)

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        dashboard_url = f"/assets/{cid_url}/"
        try:
            payload = json.loads(request.POST["payload"])
            expose(contract_id, make_did(contract_id), user_name, payload)
        except Exception as e:
            logger.exception("Failed to expose asset")
            return redirect_with_msg(dashboard_url, f"Failed to expose asset: {e}", "error")
        return redirect_with_msg(dashboard_url, "Asset exposed.", "success")


class AssetExposeStreamView(BaseView):
    """POST {cards, parameters, authorities} -- expose the asset, streaming progress."""

    http_method_names = ["post"]

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        try:
            steps = _expose_steps(contract_id, make_did(contract_id), user_name, _json_body(request))
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        return stream_steps(
            steps,
            complete=lambda ctx: {"redirect": f"/assets/{cid_url}/", "message": "Asset exposed."},
        )


# ============================================================
# JSON endpoints
# ============================================================
class AssetUseEndpoint(JsonView):
    """POST {asset_did, wallet_id, ...} — run the action this asset's guardian
    supports and return its result.

    Which flow runs, what else the payload must carry, and what comes back are all
    decided by the action runner (see ``app.action_runners``); this handler only
    checks the wallet and hands over.
    """

    def handle(self, request, data, **kwargs):
        asset_did = require(data, "asset_did")
        user_name = AppConfig.get_instance().public_key
        wallets = _clean_wallets(data, user_name)

        asset_info = registry_client.get_asset_by_did(asset_did)
        metadata = asset_info.get("metadata", {}) or {}
        _reject_federated(metadata)

        try:
            runner = action_runners.build_runner(
                user_name=user_name,
                asset_did=asset_did,
                metadata=metadata,
                wallets=wallets,
                params=data,
            )
        except ValueError as e:
            raise ValidationError(str(e))

        result = runner.run()
        return {"ok": True, "guardian_type": runner.name, **result}


class AssetUseFormEndpoint(JsonView):
    """POST {asset_did} — describe what the Use form must collect for an asset.

    The roles come from the asset's own policy, so the form cannot be rendered
    from the asset list alone; the client asks for them when the modal opens.

    Federated assets answer this too, and the Federated page asks it of every
    asset a requester selects: each site's policy decides its own roles, and the
    form has to cover the union of them.
    """

    def handle(self, request, data, **kwargs):
        asset_did = require(data, "asset_did")
        user_name = AppConfig.get_instance().public_key

        try:
            asset_info = registry_client.get_asset_by_did(asset_did)
        except Exception as e:
            raise ValidationError(f"failed to look up asset: {e}")
        metadata = (asset_info or {}).get("metadata", {}) or {}

        guardian_type = action_runners.guardian_type_of(metadata)
        try:
            runner_class = action_runners.get_runner_class(guardian_type)
        except ValueError as e:
            raise ValidationError(str(e))

        roles = []
        if runner_class.needs_wallets:
            token_did = metadata.get("policy_contract", "")
            if not token_did:
                raise ValidationError(
                    "Asset has not been exposed (no policy_contract in registry)."
                )
            token_id, _ = parse_did(token_did)
            requirements = pdo_runner.get_policy_requirements(token_id, user_name)
            templates = registry_client.credential_templates_by_type()
            roles = [
                {
                    "role": role,
                    "credential_types": sorted(set(types)),
                    "facts": [templates[t]["display_name"] for t in sorted(set(types))],
                }
                for role, types in sorted(requirements.items())
            ]

        return {
            "ok": True,
            "guardian_type": guardian_type,
            "label": runner_class.label,
            "federated": runner_class.federated,
            "roles": roles,
        }


def checklist_for(asset_did, wallets, user_name):
    """The readiness checklist of one asset, for the wallets chosen so far."""
    metadata = registry_client.get_asset_by_did(asset_did)["metadata"]
    if "policy_contract" not in metadata:
        raise ValidationError("Asset has not been exposed (no policy_contract in registry).")
    token_did = metadata["policy_contract"]
    token_id, _ = parse_did(token_did)
    assessment = readiness.assess(token_id, wallets, user_name)
    rows = [
        {
            "role": r["role"],
            "type": r["type"],
            "name": r["name"],
            "status": r["status"],
            "authorities": r["authorities"],
            "via": r["via"]["name"] if r["via"] else None,
        }
        for r in assessment["rows"]
    ]
    return {
        "rows": rows,
        "ready": assessment["ready"],
        "needs_project": assessment["needs_project"],
        "projects": assessment["projects"],
    }


class AssetChecklistEndpoint(JsonView):
    """POST {asset_did, wallets} — what the requester holds, can get on the way,
    or has to ask for, before anything is submitted."""

    def handle(self, request, data, **kwargs):
        asset_did = require(data, "asset_did")
        user_name = AppConfig.get_instance().public_key
        if not isinstance(data.get("wallets"), dict):
            raise ValidationError("'wallets' must map each role to a wallet, or to '' while none is chosen")
        wallets = {role: cid for role, cid in data["wallets"].items() if cid}
        for contract_id in wallets.values():
            if not ledger_client.user_owns_contract(user_name, contract_id):
                raise ValidationError(f"wallet not found: {contract_id}")
        return {"ok": True, **checklist_for(asset_did, wallets, user_name)}


class AssetAcceptAuthorityEndpoint(JsonView):
    """POST {did, credential_types} — accept an authority for some facts."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = require(data, "did")
        types = data.get("credential_types")
        if not isinstance(types, list) or not types:
            raise ValidationError("'credential_types' must be a non-empty list of strings")
        try:
            registrations = trust.registrations({t: [did] for t in types})
        except ValueError as e:
            raise ValidationError(str(e))

        _, policy_id = _token_and_policy(make_did(contract_id), user_name)
        for issuer_id, path, facts in registrations:
            pdo_runner.register_trusted_issuer(
                policy_id, issuer_id, user_name, path=path, credential_types=facts
            )
        return {"ok": True, "message": "Accepted for: " + ", ".join(types)}


class AssetWithdrawAuthorityEndpoint(JsonView):
    """POST {contract_id, credential_types} — stop accepting an authority for
    some facts."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        issuer_id = require(data, "contract_id")
        types = data.get("credential_types")
        if not isinstance(types, list) or not types:
            raise ValidationError("'credential_types' must be a non-empty list of strings")
        _, policy_id = _token_and_policy(make_did(contract_id), user_name)
        pdo_runner.unregister_trusted_issuer(
            policy_id, issuer_id, user_name, credential_types=types
        )
        return {"ok": True, "message": "Trust withdrawn."}


class AssetUpdatePolicyDataEndpoint(JsonView):
    """POST {policy_data: {module_id: {...}}} — replace the parameters of every
    card on the asset, each under its module id; the delivery module's slice stays
    empty. Also mirrors it into the registry."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        policy_data = data.get("policy_data")
        if not isinstance(policy_data, dict) or not all(isinstance(v, dict) for v in policy_data.values()):
            raise ValidationError("'policy_data' must map each policy to an object of its parameters")

        metadata = registry_client.get_asset_by_did(did)["metadata"]
        cards = {card["name"] for card in metadata["cards"]}
        if set(policy_data) != cards:
            raise ValidationError("'policy_data' must hold the parameters of every policy on the asset: " + ", ".join(sorted(cards)))

        templates = {t["name"]: t for t in registry_client.list_policy_templates()}
        problems = [
            f"{module_id} {problem}"
            for module_id, values in policy_data.items()
            for problem in schemas.errors(values, templates[module_id]["parameters_schema"])
        ]
        if problems:
            raise ValidationError("Parameters do not fit: " + "; ".join(problems))
        policy_data = {**policy_data, metadata["delivery"]: {}}

        _, policy_id = _token_and_policy(did, user_name)
        pdo_runner.set_policy_data(policy_id, policy_data, user_name)
        try:
            registry_client.update_asset_metadata_by_did(did, {"policy_data": policy_data})
        except Exception:
            logger.exception("Failed to mirror policy_data into registry metadata")
        return {"ok": True, "message": "Policy data updated."}


# ============================================================
# Streaming variants (live per-step progress)
# ============================================================
class AssetSetupStreamView(BaseView):
    """POST {name, data_source, guardian_type, serve_on, port} — deploy a guardian
    then register the asset, streaming progress. JS variant of
    :class:`AssetSetupView`."""

    http_method_names = ["post"]

    def post(self, request):
        data = _json_body(request)
        name = (data.get("name") or "").strip()
        data_source = (data.get("data_source") or "").strip()
        if not name or not data_source:
            return JsonResponse(
                {"error": "name and data_source are required"}, status=400
            )
        try:
            guardian_type, serve_on, port = _clean_guardian_choice(data)
            _check_ports_free(guardian_type, serve_on, port)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        user_name = AppConfig.get_instance().public_key

        def contract(ctx):
            ctx["contract_id"] = pdo_runner.create_asset_identity(name, user_name)
            ctx["did"] = make_did(ctx["contract_id"])
            return {"detail": _short_id(ctx["contract_id"])}

        def deploy(ctx):
            url, resolved_port = guardian_launcher.deploy_guardian(
                data_source,
                guardian_type=guardian_type,
                serve_on=serve_on,
                port=port,
                asset_did=ctx["did"],
                asset_name=name,
            )
            ctx["guardian_url"], ctx["guardian_port"] = url, resolved_port
            return {"detail": f"{guardian_type} guardian at {url}:{resolved_port}"}

        def wait(ctx):
            guardian_launcher.wait_until_healthy(
                ctx["guardian_url"], ctx["guardian_port"]
            )

        def register(ctx):
            did = ctx["did"]
            reg = registry_client.register_asset(
                name=name,
                did=did,
                metadata={
                    "data_source": data_source,
                    "guardian_url": ctx["guardian_url"],
                    "guardian_port": ctx["guardian_port"],
                    "guardian_type": guardian_type,
                    "serve_on": serve_on,
                },
            )
            pk = reg["id"]
            registry_client.update_asset_metadata(
                pk,
                {
                    "asset_registry_url": (
                        f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{pk}/"
                    )
                },
            )

        steps = [
            ("contract", "Creating the asset contract", contract),
            ("guardian", "Deploying the guardian", deploy),
            ("health", "Waiting for the guardian to be healthy", wait),
            ("register", "Registering the asset", register),
        ]
        return stream_steps(
            steps,
            complete=lambda ctx: {
                "redirect": "/",
                "message": (
                    f'Asset "{name}" registered behind '
                    f"{_with_article(guardian_type)} guardian."
                ),
            },
        )


class AssetUseStreamView(BaseView):
    """POST {asset_did, wallet_id, ...} — run the asset's action, streaming
    progress. The action's result is returned on the terminal event as
    ``result``, alongside ``result_kind`` telling the UI how to render it. JS
    variant of :class:`AssetUseEndpoint`."""

    http_method_names = ["post"]

    def post(self, request):
        data = _json_body(request)
        asset_did = (data.get("asset_did") or "").strip()
        if not asset_did:
            return JsonResponse({"error": "asset_did is required"}, status=400)

        user_name = AppConfig.get_instance().public_key
        try:
            wallets = _clean_wallets(data, user_name)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        try:
            asset_info = registry_client.get_asset_by_did(asset_did)
        except Exception as e:
            return JsonResponse({"error": f"failed to look up asset: {e}"}, status=400)
        metadata = (asset_info or {}).get("metadata", {}) or {}

        try:
            _reject_federated(metadata)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        try:
            runner = action_runners.build_runner(
                user_name=user_name,
                asset_did=asset_did,
                metadata=metadata,
                wallets=wallets,
                params=data,
            )
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return stream_steps(
            runner.steps(),
            complete=lambda ctx: {
                "result": runner.result(ctx),
                "result_kind": runner.result_kind,
                "guardian_type": runner.name,
                "message": f"{runner.label} completed.",
            },
        )
