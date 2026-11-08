import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Asset, Authority, TrustList


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


def _asset_to_dict(asset):
    return {
        "id": asset.pk,
        "name": asset.name,
        "did": asset.did,
        "metadata": asset.metadata,
    }


@csrf_exempt
def assets_list_create(request):
    if request.method == "GET":
        assets = list(Asset.objects.all().order_by("pk"))
        return JsonResponse([_asset_to_dict(a) for a in assets], safe=False)

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        name = data.get("name", "").strip()
        did = data.get("did", "").strip()
        metadata = data.get("metadata", {})

        if not name or not did:
            return JsonResponse({"error": "name and did are required"}, status=400)

        if Asset.objects.filter(did=did).exists():
            return JsonResponse(
                {"error": "An asset with this DID already exists"}, status=409
            )

        asset = Asset.objects.create(name=name, did=did, metadata=metadata)
        return JsonResponse(_asset_to_dict(asset), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def asset_detail(request, pk):
    try:
        asset = Asset.objects.get(pk=pk)
    except Asset.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(_asset_to_dict(asset))

    if request.method == "PATCH":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "name" in data:
            asset.name = data["name"]
        if "did" in data:
            asset.did = data["did"]
        if "metadata" in data:
            # Merge new fields into existing metadata
            existing = asset.metadata or {}
            existing.update(data["metadata"])
            asset.metadata = existing

        asset.save()
        return JsonResponse(_asset_to_dict(asset))

    if request.method == "DELETE":
        asset.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET"])
def asset_by_did(request):
    did = request.GET.get("did", "").strip()
    if not did:
        return JsonResponse({"error": "did query parameter is required"}, status=400)

    try:
        asset = Asset.objects.get(did=did)
    except Asset.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse(_asset_to_dict(asset))


# ============================================================
# Directory: authorities and trust lists
# ============================================================
AUTHORITY_FIELDS = ("did", "name", "kind", "operator", "facts", "checks", "inputs", "sources", "metadata")
TRUST_LIST_FIELDS = ("name", "maintainer", "description", "entries")


def _record_to_dict(record, fields):
    return {"id": record.pk, **{f: getattr(record, f) for f in fields}}


def _missing(data, fields):
    missing = [f for f in fields if f not in data]
    return f"missing: {', '.join(missing)}" if missing else None


def _authority_error(data):
    error = _missing(data, AUTHORITY_FIELDS)
    if error:
        return error
    if not data["did"].strip() or not data["name"].strip():
        return "did and name must not be empty"
    if data["kind"] not in Authority.KINDS:
        return f"kind must be one of {', '.join(Authority.KINDS)}"
    return None


def _trust_list_error(data):
    error = _missing(data, TRUST_LIST_FIELDS)
    if error:
        return error
    if not data["name"].strip():
        return "name must not be empty"
    entries = data["entries"]
    if not isinstance(entries, list) or not all(
        isinstance(e, dict) and isinstance(e.get("did"), str) and e["did"] and isinstance(e.get("credential_types"), list)
        for e in entries
    ):
        return "entries must be a list of {did, credential_types}"
    return None


def _list_create(request, model, fields, unique, validate):
    if request.method == "GET":
        records = [_record_to_dict(r, fields) for r in model.objects.all().order_by("pk")]
        return JsonResponse(records, safe=False)

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        error = validate(data)
        if error:
            return JsonResponse({"error": error}, status=400)
        if model.objects.filter(**{unique: data[unique]}).exists():
            return JsonResponse({"error": f"one with this {unique} already exists"}, status=409)
        record = model.objects.create(**{f: data[f] for f in fields})
        return JsonResponse(_record_to_dict(record, fields), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def _detail(request, model, fields, pk):
    try:
        record = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(_record_to_dict(record, fields))

    if request.method == "PATCH":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        for f in fields:
            if f in data:
                setattr(record, f, data[f])
        record.save()
        return JsonResponse(_record_to_dict(record, fields))

    if request.method == "DELETE":
        record.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def authorities_list_create(request):
    """GET lists every authority. POST registers one, with every field."""
    return _list_create(request, Authority, AUTHORITY_FIELDS, "did", _authority_error)


@csrf_exempt
def authority_detail(request, pk):
    return _detail(request, Authority, AUTHORITY_FIELDS, pk)


@csrf_exempt
@require_http_methods(["GET"])
def authority_by_did(request):
    did = request.GET.get("did", "").strip()
    if not did:
        return JsonResponse({"error": "did query parameter is required"}, status=400)
    try:
        return JsonResponse(_record_to_dict(Authority.objects.get(did=did), AUTHORITY_FIELDS))
    except Authority.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)


@csrf_exempt
def trust_lists_list_create(request):
    """GET lists every trust list. POST creates one, with every field."""
    return _list_create(request, TrustList, TRUST_LIST_FIELDS, "name", _trust_list_error)


@csrf_exempt
def trust_list_detail(request, pk):
    return _detail(request, TrustList, TRUST_LIST_FIELDS, pk)
