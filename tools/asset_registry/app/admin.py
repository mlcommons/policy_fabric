from django.contrib import admin

from .models import Asset, Authority, TrustList


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "did", "metadata")
    search_fields = ("name", "did")


@admin.register(Authority)
class AuthorityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind", "did", "facts")
    search_fields = ("name", "did")


@admin.register(TrustList)
class TrustListAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "maintainer")
    search_fields = ("name",)
