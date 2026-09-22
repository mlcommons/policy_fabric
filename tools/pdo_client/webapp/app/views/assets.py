import json
import logging

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
    registry_client,
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


def _resolve_policy_id(token_contract_id, user_name):
    """Return the policy agent contract id for a given token, by reading the
    token's trusted-issuer list. The token registers exactly one issuer at
    expose-time: the policy agent. Returns ``None`` if none is registered.
    """
    issuers = pdo_runner.list_token_trusted_issuers(token_contract_id, user_name)
    if not issuers:
        return None
    return next(iter(issuers.keys()))


def _flatten_policy_issuers(raw_issuers):
    """Flatten the policy agent's trusted-issuer map into display rows.

    ``raw_issuers`` is shaped as ``{contract_id: [entry, ...]}`` where each
    entry has ``verifying_context.prefix_path`` and ``credential_types``.
    Returns a list of ``{"did", "credential_types"}`` dicts, one per
    (contract_id, prefix_path) pair.
    """
    rows = []
    for contract_id, entries in (raw_issuers or {}).items():
        for entry in entries or []:
            prefix_path = (entry.get("verifying_context") or {}).get(
                "prefix_path"
            ) or []
            rows.append(
                {
                    "did": make_did(contract_id, prefix_path),
                    "credential_types": entry.get("credential_types") or [],
                }
            )
    return rows


def _short_id(contract_id, n=12):
    return contract_id[:n]


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
    contract that gives the asset its DID, start a guardian serving the given data
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
            f'Asset "{name}" registered behind a {guardian_type} guardian.',
            "success",
        )


class AssetDashboardView(BaseView):
    """GET-only: render the per-asset dashboard.

    Determines whether the asset already has a policy agent by reading the
    registry's ``policy_contract`` metadata (a token DID, set at expose time)
    and querying the token's trusted-issuer list. When a policy exists, the
    dashboard also lists its currently registered trusted issuers; otherwise
    it surfaces the Expose form.
    """

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            logger.exception("Failed to fetch asset from registry")
            asset = {}
            registry_error = str(e)
        else:
            registry_error = None

        metadata = asset.get("metadata", {}) or {}
        guardian_url = metadata.get("guardian_url", "")
        guardian_port = metadata.get("guardian_port", "")
        guardian_deployed = bool(guardian_url and guardian_port)
        # A guardian that enforces nothing has nothing to attach a policy to, so the
        # Expose form is only offered for the ones that do.
        guardian_type = action_runners.guardian_type_of(metadata)
        runner_class = action_runners.RUNNERS.get(guardian_type)
        supports_policy = bool(runner_class and runner_class.needs_policy)
        ctx = {
            "asset": {
                "contract_id": contract_id,
                "cid_url": cid_url,
                "did": did,
                "name": asset.get("name") or f"Asset {_short_id(contract_id)}",
            },
            "wallets": _user_wallet_cards(user_name),
            "guardian_deployed": guardian_deployed,
            "guardian_url": guardian_url,
            "guardian_port": guardian_port,
            "guardian_type": guardian_type,
            "serve_on": metadata.get("serve_on", ""),
            "supports_policy": supports_policy,
            "guardian_endpoint": (
                _guardian_url_port(guardian_url, guardian_port)
                if guardian_deployed
                else ""
            ),
            "has_policy": False,
            "policy_contract_id": None,
            "token_contract_id": None,
            "policy_issuers": [],
            "policy_issuers_error": None,
            "policy_data": {},
            "policy_data_json": "",
            "policy_data_error": None,
            "registry_error": registry_error,
            "templates": [],
            "templates_error": None,
            "policy_details": {},
            "credential_templates": [],
            "credential_templates_error": None,
            "credential_type_options": [],
        }

        token_did = metadata.get("policy_contract", "")
        if token_did:
            try:
                token_id, _ = parse_did(token_did)
                policy_id = _resolve_policy_id(token_id, user_name)
            except Exception as e:
                logger.exception("Failed to resolve policy id from token")
                ctx["policy_issuers_error"] = str(e)
                policy_id = None
                token_id = None

            if policy_id:
                ctx["has_policy"] = True
                ctx["policy_contract_id"] = policy_id
                ctx["token_contract_id"] = token_id
                try:
                    raw_issuers = pdo_runner.list_policy_trusted_issuers(
                        policy_id, user_name
                    )
                    ctx["policy_issuers"] = _flatten_policy_issuers(raw_issuers)
                except Exception as e:
                    logger.exception("Failed to list policy trusted issuers")
                    ctx["policy_issuers_error"] = str(e)
                try:
                    ctx["policy_data"] = pdo_runner.get_policy_data(
                        policy_id, user_name
                    )
                    ctx["policy_data_json"] = json.dumps(ctx["policy_data"], indent=2)
                except Exception as e:
                    logger.exception("Failed to get policy data")
                    ctx["policy_data_error"] = str(e)
                    ctx["policy_data_json"] = ""
                try:
                    ctx["credential_templates"] = (
                        registry_client.list_credential_templates()
                    )
                except Exception as e:
                    logger.exception("Failed to fetch credential templates")
                    ctx["credential_templates_error"] = str(e)

        if not ctx["has_policy"]:
            try:
                # only Rego-backed templates can be provisioned as subpolicies
                ctx["templates"] = [
                    t
                    for t in registry_client.list_policy_templates()
                    if (t.get("rego_source") or "").strip()
                ]
                for t in ctx["templates"]:
                    t["policy_data_schema_json"] = json.dumps(
                        t.get("policy_data_schema") or {}
                    )
                # rego source + README per policy, for the "View" popup (keyed by id)
                ctx["policy_details"] = {
                    str(t["id"]): {
                        "name": t.get("name", ""),
                        "rego_source": t.get("rego_source", ""),
                        "readme": t.get("readme", ""),
                    }
                    for t in ctx["templates"]
                }
            except Exception as e:
                logger.exception("Failed to fetch policy templates")
                ctx["templates_error"] = str(e)

            # Credential types the expose form's inline "trusted issuers" section
            # offers as checkboxes.
            try:
                ctx["credential_templates"] = (
                    registry_client.list_credential_templates()
                )
                ctx["credential_type_options"] = [
                    t.get("template_type") for t in ctx["credential_templates"]
                ]
            except Exception as e:
                logger.exception("Failed to fetch credential templates")
                ctx["credential_templates_error"] = str(e)

        return render(request, "assets/dashboard.html", ctx)


class AssetExposeView(BaseView):
    """POST-only now: create policy + token contracts, set policy data, and
    update the registry. The form lives inside the dashboard page; on success
    we redirect back there.
    """

    def get(self, request, cid_url):
        return redirect("asset_dashboard", cid_url=cid_url)

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)
        dashboard_url = f"/assets/{cid_url}/"

        policy_data_raw = (request.POST.get("policy_data") or "").strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return redirect_with_msg(
                dashboard_url, f"Invalid policy data JSON: {e}", "error"
            )

        # Trusted issuers added inline in the expose form (optional). The JS
        # serializes each box as {"did", "credential_types": [...]} into a hidden
        # field; they are registered on the new policy after it is created.
        trusted_issuers_raw = (request.POST.get("trusted_issuers") or "").strip()
        try:
            trusted_issuers = json.loads(trusted_issuers_raw) if trusted_issuers_raw else []
        except json.JSONDecodeError:
            trusted_issuers = []
        if not isinstance(trusted_issuers, list):
            trusted_issuers = []

        # The owner may select one or more policy templates; each becomes a Rego
        # subpolicy provisioned into the rego_policy_agent via set_rego_policy.
        policy_template_ids = request.POST.getlist("policy_templates")
        if not policy_template_ids:
            return redirect_with_msg(
                dashboard_url, "Select at least one policy.", "error"
            )

        try:
            rego_modules = []
            for tid in policy_template_ids:
                tpl = registry_client.get_policy_template(tid)
                source = (tpl.get("rego_source") or "").strip()
                if not source:
                    return redirect_with_msg(
                        dashboard_url,
                        f"Policy '{tpl.get('name', tid)}' has no rego source.",
                        "error",
                    )
                rego_modules.append([tpl["name"], source])
        except Exception as e:
            logger.exception("Failed to load selected policy templates")
            return redirect_with_msg(
                dashboard_url, f"Failed to load selected policies: {e}", "error"
            )

        # Guardian info is on the registry record (set at asset registration).
        try:
            meta = (registry_client.get_asset_by_did(did) or {}).get(
                "metadata", {}
            ) or {}
        except Exception as e:
            return redirect_with_msg(
                dashboard_url, f"Failed to read asset metadata: {e}", "error"
            )
        guardian_host = meta.get("guardian_url", "")
        guardian_port = meta.get("guardian_port", "")
        if not guardian_host or not guardian_port:
            return redirect_with_msg(
                dashboard_url, "Guardian URL/port missing on this asset.", "error"
            )

        guardian = _guardian_url_port(guardian_host, guardian_port)
        asset_name = meta.get("name") or _short_id(contract_id)

        try:
            result = pdo_runner.create_asset_policy(
                f"Policy for {asset_name}", guardian, user_name, rego_modules
            )

            if policy_data:
                pdo_runner.set_policy_data(
                    result["policy_contract_id"], policy_data, user_name
                )

            token_did = make_did(result["token_contract_id"])
            registry_client.update_asset_metadata_by_did(
                did,
                {"policy_contract": token_did, "policy_data": policy_data},
            )

        except Exception as e:
            logger.exception("Failed to expose asset")
            return redirect_with_msg(
                dashboard_url, f"Failed to expose asset: {e}", "error"
            )

        # The asset is now exposed; register any trusted issuers from the form as
        # a best effort. A failed issuer is reported but doesn't undo the expose —
        # it can be added later from the dashboard's Trusted Issuers section.
        policy_id = result["policy_contract_id"]
        issuer_errors = []
        for entry in trusted_issuers:
            if not isinstance(entry, dict):
                continue
            entry_did = (entry.get("did") or "").strip()
            credential_types = entry.get("credential_types") or []
            if not entry_did or not credential_types:
                continue
            try:
                issuer_contract_id, issuer_path = parse_did(entry_did)
                pdo_runner.register_policy_trusted_issuer(
                    policy_id,
                    issuer_contract_id,
                    user_name,
                    path=[issuer_path] if issuer_path else [],
                    credential_types=credential_types,
                )
            except Exception as e:
                logger.exception("Failed to register trusted issuer %s", entry_did)
                issuer_errors.append(f"{entry_did}: {e}")

        if issuer_errors:
            return redirect_with_msg(
                dashboard_url,
                "Asset exposed, but some trusted issuers failed: "
                + "; ".join(issuer_errors),
                "error",
            )

        return redirect_with_msg(
            dashboard_url, "Asset exposed via rego policy.", "success"
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
            roles = [
                {"role": role, "credential_types": sorted(set(types))}
                for role, types in sorted(requirements.items())
            ]

        return {
            "ok": True,
            "guardian_type": guardian_type,
            "label": runner_class.label,
            "federated": runner_class.federated,
            "roles": roles,
        }


class AssetRegisterPolicyIssuerEndpoint(JsonView):
    """POST {issuer_did, credential_types: [...]} — register a signature
    authority (identified by its DID, optionally with a ``#path`` signing
    context) as a trusted issuer for one or more credential types on the
    asset's policy agent.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        issuer_did = require(data, "issuer_did")
        credential_types = data.get("credential_types")
        if not isinstance(credential_types, list) or not credential_types:
            raise ValidationError(
                "'credential_types' must be a non-empty list of strings"
            )

        try:
            issuer_contract_id, issuer_path = parse_did(issuer_did)
        except ValueError as e:
            raise ValidationError(str(e))
        path = [issuer_path] if issuer_path else []

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            raise ValidationError(f"failed to look up asset in registry: {e}")
        token_did = (asset.get("metadata", {}) or {}).get("policy_contract", "")
        if not token_did:
            raise ValidationError("Asset has no policy agent yet (expose it first).")

        token_id, _ = parse_did(token_did)
        policy_id = _resolve_policy_id(token_id, user_name)
        if not policy_id:
            raise ValidationError("Token contract has no registered policy agent.")

        pdo_runner.register_policy_trusted_issuer(
            policy_id,
            issuer_contract_id,
            user_name,
            path=path,
            credential_types=credential_types,
        )
        return {
            "ok": True,
            "message": "Issuer registered for: " + ", ".join(credential_types),
        }


class AssetUpdatePolicyDataEndpoint(JsonView):
    """POST {policy_data: {...}} — call set_policy_data on the asset's policy
    agent. Also mirrors the new data into the asset registry metadata so the
    list view's policy_data field stays in sync.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        policy_data = data.get("policy_data")
        if not isinstance(policy_data, dict):
            raise ValidationError("'policy_data' must be a JSON object")

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            raise ValidationError(f"failed to look up asset in registry: {e}")
        token_did = (asset.get("metadata", {}) or {}).get("policy_contract", "")
        if not token_did:
            raise ValidationError("Asset has no policy agent yet (expose it first).")

        token_id, _ = parse_did(token_did)
        policy_id = _resolve_policy_id(token_id, user_name)
        if not policy_id:
            raise ValidationError("Token contract has no registered policy agent.")

        pdo_runner.set_policy_data(policy_id, policy_data, user_name)

        try:
            registry_client.update_asset_metadata_by_did(
                did, {"policy_data": policy_data}
            )
        except Exception:
            logger.exception("Failed to mirror policy_data into registry metadata")

        return {"ok": True, "message": "Policy data updated."}


# ============================================================
# Streaming variants (live per-step progress)
#
# Same work as the register / expose / use handlers above, but emitted as a
# stream of progress steps (see app/views/_streaming.py) so the UI can show what
# is happening behind the scenes. The page-form / JSON handlers above remain as
# the plain fallbacks.
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
                "message": f'Asset "{name}" registered behind a {guardian_type} guardian.',
            },
        )


class AssetExposeStreamView(BaseView):
    """POST {policy_templates: [...], policy_data, trusted_issuers: [...]} —
    create the policy + token, set data, update the registry, and register
    trusted issuers, streaming progress. JS variant of :class:`AssetExposeView`."""

    http_method_names = ["post"]

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)
        dashboard_url = f"/assets/{cid_url}/"

        data = _json_body(request)
        policy_template_ids = data.get("policy_templates") or []
        if not isinstance(policy_template_ids, list) or not policy_template_ids:
            return JsonResponse({"error": "Select at least one policy."}, status=400)

        policy_data_raw = (data.get("policy_data") or "").strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return JsonResponse({"error": f"Invalid policy data JSON: {e}"}, status=400)

        trusted_issuers = data.get("trusted_issuers") or []
        if not isinstance(trusted_issuers, list):
            trusted_issuers = []

        def load(ctx):
            rego_modules = []
            for tid in policy_template_ids:
                tpl = registry_client.get_policy_template(tid)
                source = (tpl.get("rego_source") or "").strip()
                if not source:
                    raise ValueError(
                        f"Policy '{tpl.get('name', tid)}' has no rego source."
                    )
                rego_modules.append([tpl["name"], source])
            meta = (registry_client.get_asset_by_did(did) or {}).get(
                "metadata", {}
            ) or {}
            host, port = meta.get("guardian_url", ""), meta.get("guardian_port", "")
            if not host or not port:
                raise ValueError("Guardian URL/port missing on this asset.")
            ctx["rego_modules"] = rego_modules
            ctx["guardian"] = _guardian_url_port(host, port)
            ctx["asset_name"] = meta.get("name") or _short_id(contract_id)
            return {"detail": f"{len(rego_modules)} policy(ies)"}

        def create_policy(ctx):
            result = pdo_runner.create_asset_policy(
                f"Policy for {ctx['asset_name']}",
                ctx["guardian"],
                user_name,
                ctx["rego_modules"],
            )
            ctx["policy_id"] = result["policy_contract_id"]
            ctx["token_id"] = result["token_contract_id"]

        def set_data(ctx):
            if not policy_data:
                raise SkipStep("no policy data provided")
            pdo_runner.set_policy_data(ctx["policy_id"], policy_data, user_name)

        def update_registry(ctx):
            registry_client.update_asset_metadata_by_did(
                did,
                {"policy_contract": make_did(ctx["token_id"]), "policy_data": policy_data},
            )

        def register_issuers(ctx):
            entries = [
                e
                for e in trusted_issuers
                if isinstance(e, dict)
                and (e.get("did") or "").strip()
                and (e.get("credential_types") or [])
            ]
            if not entries:
                raise SkipStep("none provided")
            errors = []
            for entry in entries:
                entry_did = entry["did"].strip()
                try:
                    issuer_contract_id, issuer_path = parse_did(entry_did)
                    pdo_runner.register_policy_trusted_issuer(
                        ctx["policy_id"],
                        issuer_contract_id,
                        user_name,
                        path=[issuer_path] if issuer_path else [],
                        credential_types=entry["credential_types"],
                    )
                except Exception as e:
                    logger.exception("Failed to register trusted issuer %s", entry_did)
                    errors.append(f"{entry_did}: {e}")
            if errors:
                return {"detail": "some issuers failed: " + "; ".join(errors)}
            return {"detail": f"{len(entries)} issuer(s)"}

        steps = [
            ("load", "Loading the selected policies", load),
            ("policy", "Creating the policy and token contracts", create_policy),
            ("data", "Setting the policy data", set_data),
            ("registry", "Updating the asset registry", update_registry),
            ("issuers", "Registering trusted issuers", register_issuers),
        ]
        return stream_steps(
            steps,
            complete=lambda ctx: {
                "redirect": dashboard_url,
                "message": "Asset exposed via rego policy.",
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
