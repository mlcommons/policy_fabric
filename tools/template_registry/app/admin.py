from django.contrib import admin

from .models import CredentialTemplate, PolicyTemplate


@admin.register(PolicyTemplate)
class PolicyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(CredentialTemplate)
class CredentialTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "template_type")
    search_fields = ("template_type",)
