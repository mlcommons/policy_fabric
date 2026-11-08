from django.urls import path
from . import views

urlpatterns = [
    path("policies/", views.policies_list_create, name="policies_list_create"),
    path("policies/<int:pk>/", views.policy_detail, name="policy_detail"),
    path("authorities/", views.authorities_list, name="authorities_list"),
    path("authorities/<int:pk>/", views.authority_detail, name="authority_detail"),
    path("credentials/", views.credentials_list_create, name="credentials_list_create"),
    path("credentials/<int:pk>/", views.credential_detail, name="credential_detail"),
]
