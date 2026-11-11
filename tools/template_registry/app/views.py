import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import catalog
from .models import CredentialTemplate, PolicyComponent, PolicyTemplate

POLICY_FIELDS = (
    "name",
    "code",
    "title",
    "rule",
    "guardian_types",
    "readme",
    "graph",
)

COMPONENT_FIELDS = (
    "component_id",
    "package",
    "rego_source",
    "metadata",
    "policy_data_schema",
)

CREDENTIAL_FIELDS = (
    "template_type",
    "display_name",
    "meaning",
    "subject_kinds",
    "self_asserted",
    "json_schema",
    "claims_schema",
    "presentable",
)


def _to_dict(tpl, fields):
    return {"id": tpl.pk, **{field: getattr(tpl, field) for field in fields}}


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


def _detail(model, fields, pk):
    try:
        return JsonResponse(_to_dict(model.objects.get(pk=pk), fields))
    except model.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)


@csrf_exempt
def policies_list_create(request):
    """GET lists policy templates, filtered by ``guardian_type`` (the templates
    that can sit in front of that guardian). POST creates one, whose graph is
    checked first."""
    if request.method == "GET":
        templates = PolicyTemplate.objects.all().order_by("pk")
        guardian_type = request.GET.get("guardian_type")
        out = [_to_dict(t, POLICY_FIELDS) for t in templates]
        if guardian_type:
            out = [t for t in out if guardian_type in t["guardian_types"]]
        return JsonResponse(out, safe=False)

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)
        if PolicyTemplate.objects.filter(name=name).exists():
            return JsonResponse(
                {"error": "A policy template with this name already exists"}, status=409
            )
        if not isinstance(data.get("graph"), dict):
            return JsonResponse({"error": "graph is required"}, status=400)
        problems = catalog.graph_problems(name, data["graph"])
        if problems:
            return JsonResponse({"error": "The graph is not valid", "problems": problems}, status=400)
        values = {f: data[f] for f in POLICY_FIELDS if f in data and f != "name"}
        tpl = PolicyTemplate.objects.create(name=name, **values)
        return JsonResponse(_to_dict(tpl, POLICY_FIELDS), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET"])
def policy_detail(request, pk):
    return _detail(PolicyTemplate, POLICY_FIELDS, pk)


@csrf_exempt
@require_http_methods(["GET"])
def components_list(request):
    """GET lists every policy component: its Rego, its component.json and the JSON Schema
    of its policy data."""
    components = PolicyComponent.objects.all().order_by("component_id")
    return JsonResponse([_to_dict(c, COMPONENT_FIELDS) for c in components], safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def catalog_detail(request):
    """GET the policy catalog of the seeded folders, which the webapp draws graphs from."""
    try:
        return JsonResponse(catalog.catalog())
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def credentials_list_create(request):
    if request.method == "GET":
        templates = CredentialTemplate.objects.all().order_by("pk")
        return JsonResponse([_to_dict(t, CREDENTIAL_FIELDS) for t in templates], safe=False)

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        template_type = (data.get("template_type") or "").strip()
        if not template_type or data.get("claims_schema") is None:
            return JsonResponse(
                {"error": "template_type and claims_schema are required"}, status=400
            )
        if CredentialTemplate.objects.filter(template_type=template_type).exists():
            return JsonResponse(
                {"error": "A credential template with this type already exists"},
                status=409,
            )
        values = {f: data[f] for f in CREDENTIAL_FIELDS if f in data and f != "template_type"}
        tpl = CredentialTemplate.objects.create(template_type=template_type, **values)
        return JsonResponse(_to_dict(tpl, CREDENTIAL_FIELDS), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET"])
def credential_detail(request, pk):
    return _detail(CredentialTemplate, CREDENTIAL_FIELDS, pk)
