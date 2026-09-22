from django.db import models


class AppConfig(models.Model):
    """Singleton application configuration.

    Only the user identity is stored here. Service URLs (ledger, asset
    registry, template registry) are deployment configuration and come from
    the environment via Django settings, not from this table.
    """

    public_key = models.TextField(default="")  # user identity (username for now)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_configured(self):
        return bool(self.public_key)

    def __str__(self):
        return f"AppConfig(pk={self.pk})"


class ContractName(models.Model):
    """Local (DID -> name) mapping for wallets and issuers.

    Purely a local UI convenience: the ledger's contract list has no notion
    of a display name, so the webapp remembers one here, keyed by DID.
    """

    did = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.did})"
