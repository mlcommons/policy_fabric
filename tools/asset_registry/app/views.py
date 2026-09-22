import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Asset


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
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
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
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
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
