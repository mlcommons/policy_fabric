import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _require_env(name):
    """Return the named environment variable or raise.

    All configuration is passed via the environment; run.sh / run_docker.sh
    take it as args and export it before launch (there is no .env file).
    Settings load during django.setup(), before any pdo.* import, so the
    environment is fully prepared by the time those modules load.
    """
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(f"Required environment variable {name} is not set")


SECRET_KEY = "django-insecure-client-app-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# The single signing context every manual issuer is set up with at creation
# time. The webapp no longer exposes signing-context management in the UI —
# credentials are always signed from this one context.
POC_SIGNING_CONTEXT_NAME = "poc"

# Since Django 4.0 the CSRF check validates the request Origin against this list
# whenever the request arrives over HTTPS. A plain-HTTP localhost run skips the
# check, but GitHub Codespaces forwards the port through an HTTPS tunnel, so
# POSTs are rejected unless the forwarded origin is trusted. Trust localhost on
# both schemes and the Codespaces port-forwarding domains; extra origins can be
# appended via the CSRF_TRUSTED_ORIGINS env var (comma-separated).
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "https://localhost:8000",
    "http://127.0.0.1:8000",
    "https://127.0.0.1:8000",
]
_extra_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _extra_csrf_origins:
    CSRF_TRUSTED_ORIGINS += [
        o.strip() for o in _extra_csrf_origins.split(",") if o.strip()
    ]

# -----------------------------------------------------------------
# PDO + service configuration (formerly app/pdo_config.py).
# Every value is required and read from the environment; there are no defaults.
# -----------------------------------------------------------------
PDO_LEDGER_URL = _require_env("PDO_LEDGER_URL")
PDO_LEDGER_TYPE = _require_env("PDO_LEDGER_TYPE")
F_SERVICE_HOST = _require_env("F_SERVICE_HOST")
LEDGER_CERT_PATH = _require_env("LEDGER_CERT_PATH")
SITE_TOML_SOURCE = _require_env("SITE_TOML_SOURCE")
USER_KEYS_FOLDER = _require_env("USER_KEYS_FOLDER")
PREFERRED_ESERVICE_URL = _require_env("PREFERRED_ESERVICE_URL")
ASSET_REGISTRY_URL = _require_env("ASSET_REGISTRY_URL")
TEMPLATE_REGISTRY_URL = _require_env("TEMPLATE_REGISTRY_URL")
SCRATCH_DIR = _require_env("SCRATCH_DIR")
F_LOGFILE = _require_env("PDO_LOG_FILE")
F_LOGLEVEL = _require_env("PDO_LOG_LEVEL")

# PDO install roots are expected in the environment (set in the image; exported
# by the caller for a bare-metal run). PDO_CONTRACTS_ROOT is consumed by the
# pdo.* layer, so validate it here too.
PDO_INSTALL_ROOT = _require_env("PDO_INSTALL_ROOT")
_require_env("PDO_CONTRACTS_ROOT")
PDO_HOME = f"{PDO_INSTALL_ROOT}/opt/pdo"
PDO_LEDGER_KEY_ROOT = f"{PDO_HOME}/etc/keys/ledger"
F_SERVICE_SITE_FILE = f"{PDO_HOME}/etc/sites/{F_SERVICE_HOST}.toml"

# pdo.* libraries read these from the process environment at import time, so
# mirror the resolved values into os.environ before any pdo.* import.
os.environ["PDO_HOME"] = PDO_HOME
os.environ["PDO_LEDGER_KEY_ROOT"] = PDO_LEDGER_KEY_ROOT
os.environ["PDO_LEDGER_TYPE"] = PDO_LEDGER_TYPE
os.environ["PDO_LEDGER_URL"] = PDO_LEDGER_URL

# Derived file locations under the (env-provided) scratch directory.
DOWNLOAD_OUTPUT_DIR = os.path.join(SCRATCH_DIR, "downloads")
F_SERVICE_GROUPS_DB_FILE = f"{SCRATCH_DIR}/groups_db"
F_SERVICE_DB_FILE = f"{SCRATCH_DIR}/service_db"

# Per-(user, wallet) session keys (RSA key pairs an external_key_authority
# binds to a wallet to receive downloaded data). Each wallet's keys live
# under SESSION_KEYS_DIR/<user_name>/<wallet_id>/.
SESSION_KEYS_DIR = os.path.join(SCRATCH_DIR, "session_keys")

# Guardian deployment: registering an asset also starts a guardian for it, and the
# owner picks which kind at registration time. The kinds are not listed here — each
# one is a folder under GUARDIANS_DIR carrying a run.sh and a guardian.json manifest
# describing how to launch it, and the webapp discovers them by reading that
# directory (see app/guardian_registry.py). It defaults to the sibling guardians
# directory in the repo but must be overridden (to a host path) when the webapp runs
# in a container, since the commands run on the host.
GUARDIANS_DIR = os.environ.get(
    "GUARDIANS_DIR", str(BASE_DIR.parent.parent / "guardians")
)
DEFAULT_GUARDIAN_TYPE = os.environ.get("DEFAULT_GUARDIAN_TYPE", "download")

# The port the registration form starts on. The storage service port a PDO
# guardian also needs is derived from the chosen port rather than configured, so
# that two guardians on different ports do not collide on one storage port.
GUARDIAN_PORT = os.environ.get("GUARDIAN_PORT", "7900")

# Where a guardian listens, and the host everyone else uses to reach it. The two
# differ because binding every interface says nothing about which address is
# routable, so the owner picks the intent and the launcher derives both:
#
#   localhost   bind loopback; reachable as "localhost"
#   0.0.0.0     bind every interface; reachable at F_SERVICE_HOST
#   HOSTNAME    bind every interface; reachable at this machine's hostname
SERVE_ON_CHOICES = ("localhost", "0.0.0.0", "HOSTNAME")
DEFAULT_SERVE_ON = "0.0.0.0"

# The FL server the Federated page offers first. It is a default, not a setting
# the flow reads: a federated round is submitted to a server the requester names,
# and the page lets them name a different one. The server is expected to be
# running already — the webapp joins a federation, it does not convene one.
FL_SERVER_URL = os.environ.get("FL_SERVER_URL", "http://localhost:7920")

# How the inference guardian's container names the FL server. It is passed to the
# guardian's run.sh rather than used by the webapp: a container cannot reach a
# host-published port as "localhost", so this defaults to the host gateway alias
# run.sh maps in.
FL_SERVER_URL_FROM_GUARDIAN = os.environ.get(
    "FL_SERVER_URL_FROM_GUARDIAN", "http://host.docker.internal:7920"
)

# What the webapp needs in order to start an FL server itself, for the case where
# the address above has nothing answering on it and there is no one else to ask.
# Like GUARDIANS_DIR this is a *host* path — the command runs on the host — so it
# must be overridden when the webapp runs in a container.
FL_SERVER_DIR = os.environ.get(
    "FL_SERVER_DIR", str(Path(GUARDIANS_DIR).parent / "fl_server")
)
FL_SERVER_IMAGE = os.environ.get("FL_SERVER_IMAGE", "mlcommons/pdo_fl_server:v2")

# When the webapp itself runs inside a container it has no Docker access, so it
# cannot run the guardian directly. Instead it writes the guardian command as a
# shell script into GUARDIAN_DEPLOY_DIR (a directory shared with the host); the
# host-side webapp launcher watches that directory and runs each script. When
# not containerized, the webapp runs the guardian command itself.
CONTAINERIZED_DEPLOYMENT = os.environ.get("CONTAINERIZED_DEPLOYMENT", "").lower() in (
    "1",
    "true",
    "yes",
)
GUARDIAN_DEPLOY_DIR = os.environ.get(
    "GUARDIAN_DEPLOY_DIR", os.path.join(SCRATCH_DIR, "guardian_requests")
)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "app.apps.ClientAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "app.context_processors.app_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
