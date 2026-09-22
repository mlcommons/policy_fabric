from django.urls import path

from .views.assets import (
    AssetDashboardView,
    AssetExposeStreamView,
    AssetExposeView,
    AssetRegisterPolicyIssuerEndpoint,
    AssetSetupStreamView,
    AssetSetupView,
    AssetsListView,
    AssetUpdatePolicyDataEndpoint,
    AssetUseEndpoint,
    AssetUseFormEndpoint,
    AssetUseStreamView,
)
from .views.config import ConfigPageView, IdentityProvisionView, IdentitySetView
from .views.federated import (
    FederatedPageView,
    FederatedRolesEndpoint,
    FederatedRunStreamView,
    FederatedSitesEndpoint,
    FederatedStartServerStreamView,
)
from .views.issuers import (
    IssuerAddVCEndpoint,
    IssuerDetailView,
    IssuerSignCredentialEndpoint,
    IssuersListView,
    IssuerUpdateNameEndpoint,
)
from .views.wallets import (
    WalletAddVCEndpoint,
    WalletDetailView,
    WalletSignCredentialEndpoint,
    WalletsListView,
    WalletUpdateNameEndpoint,
)

# Two URL families:
#   * Page URLs: GET renders, POST handles the page's one primary form
#     (then redirects). Used when a page has at most one logical action.
#   * /api/... endpoints: POST-only, accept and return JSON. Used by JS
#     for pages where multiple distinct actions are possible.
#
# Wallets/assets/issuers are addressed by their on-ledger contract_id.
# Because PDO contract ids are base64 hashes (containing `/`, `+`, `=`), we
# carry them through URL paths under their URL-safe encoding
# (`app.url_safe_id`) bound to the `cid_url` kwarg. Views decode it
# back to the raw contract_id at the boundary.
urlpatterns = [
    # Assets (pages)
    path("", AssetsListView.as_view(), name="assets_page"),
    path("assets/setup/", AssetSetupView.as_view(), name="asset_setup"),
    path(
        "assets/setup/stream/",
        AssetSetupStreamView.as_view(),
        name="asset_setup_stream",
    ),
    path(
        "assets/<str:cid_url>/",
        AssetDashboardView.as_view(),
        name="asset_dashboard",
    ),
    path(
        "assets/<str:cid_url>/expose/",
        AssetExposeView.as_view(),
        name="asset_expose",
    ),
    path(
        "assets/<str:cid_url>/expose/stream/",
        AssetExposeStreamView.as_view(),
        name="asset_expose_stream",
    ),
    # Federated (page)
    path("federated/", FederatedPageView.as_view(), name="federated"),
    # Wallets (pages)
    path("wallets/", WalletsListView.as_view(), name="wallets"),
    path(
        "wallets/<str:cid_url>/",
        WalletDetailView.as_view(),
        name="wallet_detail",
    ),
    # Issuers (pages)
    path("issuers/", IssuersListView.as_view(), name="issuers"),
    path(
        "issuers/<str:cid_url>/",
        IssuerDetailView.as_view(),
        name="issuer_detail",
    ),
    # Config + identity (pages)
    path("config/", ConfigPageView.as_view(), name="config"),
    path("identity/set/", IdentitySetView.as_view(), name="identity_set"),
    path(
        "identity/provision/",
        IdentityProvisionView.as_view(),
        name="identity_provision",
    ),
    # JSON endpoints
    path("api/assets/use/", AssetUseEndpoint.as_view(), name="api_asset_use"),
    path(
        "api/assets/use-form/",
        AssetUseFormEndpoint.as_view(),
        name="api_asset_use_form",
    ),
    path(
        "api/assets/use/stream/",
        AssetUseStreamView.as_view(),
        name="api_asset_use_stream",
    ),
    path(
        "api/federated/sites/",
        FederatedSitesEndpoint.as_view(),
        name="api_federated_sites",
    ),
    path(
        "api/federated/roles/",
        FederatedRolesEndpoint.as_view(),
        name="api_federated_roles",
    ),
    path(
        "api/federated/run/stream/",
        FederatedRunStreamView.as_view(),
        name="api_federated_run_stream",
    ),
    path(
        "api/federated/start-server/stream/",
        FederatedStartServerStreamView.as_view(),
        name="api_federated_start_server_stream",
    ),
    path(
        "api/assets/<str:cid_url>/register-policy-issuer/",
        AssetRegisterPolicyIssuerEndpoint.as_view(),
        name="api_asset_register_policy_issuer",
    ),
    path(
        "api/assets/<str:cid_url>/update-policy-data/",
        AssetUpdatePolicyDataEndpoint.as_view(),
        name="api_asset_update_policy_data",
    ),
    path(
        "api/wallets/<str:cid_url>/add-vc/",
        WalletAddVCEndpoint.as_view(),
        name="api_wallet_add_vc",
    ),
    path(
        "api/wallets/<str:cid_url>/sign-credential/",
        WalletSignCredentialEndpoint.as_view(),
        name="api_wallet_sign_credential",
    ),
    path(
        "api/wallets/<str:cid_url>/update-name/",
        WalletUpdateNameEndpoint.as_view(),
        name="api_wallet_update_name",
    ),
    path(
        "api/issuers/<str:cid_url>/add-vc/",
        IssuerAddVCEndpoint.as_view(),
        name="api_issuer_add_vc",
    ),
    path(
        "api/issuers/<str:cid_url>/update-name/",
        IssuerUpdateNameEndpoint.as_view(),
        name="api_issuer_update_name",
    ),
    path(
        "api/issuers/<str:cid_url>/sign-credential/",
        IssuerSignCredentialEndpoint.as_view(),
        name="api_issuer_sign_credential",
    ),
]
