from django.urls import path
from . import views

urlpatterns = [
    path("policies/", views.policies_list_create, name="policies_list_create"),
    path("policies/<int:pk>/", views.policy_detail, name="policy_detail"),
    path("credentials/", views.credentials_list_create, name="credentials_list_create"),
    path("credentials/<int:pk>/", views.credential_detail, name="credential_detail"),
]
