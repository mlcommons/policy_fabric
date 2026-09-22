from . import identity
from .models import AppConfig


def app_context(request):
    config = AppConfig.get_instance()
    user_name = config.public_key
    return {
        "app_config": config,
        "current_identity": user_name,
        "available_identities": identity.list_available_identities(),
    }
