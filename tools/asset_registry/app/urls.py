from django.urls import path
from . import views

urlpatterns = [
    path("assets/", views.assets_list_create, name="assets_list_create"),
    path("assets/by_did/", views.asset_by_did, name="asset_by_did"),
    path("assets/<int:pk>/", views.asset_detail, name="asset_detail"),
    path("authorities/", views.authorities_list_create, name="authorities_list_create"),
    path("authorities/by_did/", views.authority_by_did, name="authority_by_did"),
    path("authorities/<int:pk>/", views.authority_detail, name="authority_detail"),
    path("trust_lists/", views.trust_lists_list_create, name="trust_lists_list_create"),
    path("trust_lists/<int:pk>/", views.trust_list_detail, name="trust_list_detail"),
]
