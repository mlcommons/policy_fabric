from django.urls import path
from . import views

urlpatterns = [
    path("assets/", views.assets_list_create, name="assets_list_create"),
    path("assets/by_did/", views.asset_by_did, name="asset_by_did"),
    path("assets/<int:pk>/", views.asset_detail, name="asset_detail"),
]
