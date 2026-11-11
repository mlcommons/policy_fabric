from django.contrib import admin

from .models import CredentialTemplate, PolicyComponent, PolicyTemplate


@admin.register(PolicyTemplate)
class PolicyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code")
    search_fields = ("name", "code")


@admin.register(PolicyComponent)
class PolicyComponentAdmin(admin.ModelAdmin):
    list_display = ("id", "component_id", "package")
    search_fields = ("component_id",)


@admin.register(CredentialTemplate)
class CredentialTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "template_type", "display_name")
    search_fields = ("template_type", "display_name")
