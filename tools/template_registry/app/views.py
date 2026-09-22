import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import PolicyTemplate, CredentialTemplate


def _policy_to_dict(tpl):
    return {
        "id": tpl.pk,
        "name": tpl.name,
        "policy_data_schema": tpl.policy_data_schema,
        "rego_source": tpl.rego_source,
        "readme": tpl.readme,
    }


def _credential_to_dict(tpl):
    return {
        "id": tpl.pk,
        "template_type": tpl.template_type,
        "claims_schema": tpl.claims_schema,
    }


@csrf_exempt
def policies_list_create(request):
    if request.method == "GET":
        templates = list(PolicyTemplate.objects.all().order_by("pk"))
        return JsonResponse([_policy_to_dict(t) for t in templates], safe=False)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)

        if PolicyTemplate.objects.filter(name=name).exists():
            return JsonResponse(
                {"error": "A policy template with this name already exists"}, status=409
            )

        tpl = PolicyTemplate.objects.create(
            name=name,
            policy_data_schema=data.get("policy_data_schema", {}),
            rego_source=data.get("rego_source", ""),
            readme=data.get("readme", ""),
        )
        return JsonResponse(_policy_to_dict(tpl), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET"])
def policy_detail(request, pk):
    try:
        tpl = PolicyTemplate.objects.get(pk=pk)
    except PolicyTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse(_policy_to_dict(tpl))


@csrf_exempt
def credentials_list_create(request):
    if request.method == "GET":
        templates = list(CredentialTemplate.objects.all().order_by("pk"))
        return JsonResponse([_credential_to_dict(t) for t in templates], safe=False)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        template_type = data.get("template_type", "").strip()
        claims_schema = data.get("claims_schema")
        if not template_type or claims_schema is None:
            return JsonResponse(
                {"error": "template_type and claims_schema are required"}, status=400
            )

        if CredentialTemplate.objects.filter(template_type=template_type).exists():
            return JsonResponse(
                {"error": "A credential template with this type already exists"},
                status=409,
            )

        tpl = CredentialTemplate.objects.create(
            template_type=template_type,
            claims_schema=claims_schema,
        )
        return JsonResponse(_credential_to_dict(tpl), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@require_http_methods(["GET"])
def credential_detail(request, pk):
    try:
        tpl = CredentialTemplate.objects.get(pk=pk)
    except CredentialTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse(_credential_to_dict(tpl))
