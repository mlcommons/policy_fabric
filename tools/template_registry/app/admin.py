from django.contrib import admin

from .models import AuthorityTemplate, CredentialTemplate, PolicyTemplate


@admin.register(PolicyTemplate)
class PolicyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind", "code")
    search_fields = ("name", "code")


@admin.register(AuthorityTemplate)
class AuthorityTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "issues")
    search_fields = ("name", "issues")


@admin.register(CredentialTemplate)
class CredentialTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "template_type", "display_name")
    search_fields = ("template_type", "display_name")
