from django.db import models


class Asset(models.Model):
    name = models.CharField(max_length=200)
    did = models.CharField(max_length=500, unique=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Authority(models.Model):
    """A directory entry for an authority: who it is and which facts it issues.

    Discovery only. Trust is recorded on each policy agent, with the key read
    from the authority's own contract; this record is how an owner finds the
    authority to trust.
    """

    HAND_SIGNING = "hand-signing"
    RULE_BASED = "rule-based"
    SYSTEM = "system"
    KINDS = (HAND_SIGNING, RULE_BASED, SYSTEM)

    did = models.CharField(max_length=500, unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20)
    operator = models.CharField(max_length=200, default="")
    # the credential types it issues
    facts = models.JSONField(default=list)
    # what it checks, in a sentence
    checks = models.TextField(default="")
    # rule-based: the inputs it reads and the authorities it accepts for them
    inputs = models.JSONField(default=dict)
    sources = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class TrustList(models.Model):
    """A named set of authorities, accepted in one click.

    entries: [ { "did": <authority DID>, "credential_types": [...] }, ... ]
    """

    name = models.CharField(max_length=200, unique=True)
    maintainer = models.CharField(max_length=200, default="")
    description = models.TextField(default="")
    entries = models.JSONField(default=list)

    def __str__(self):
        return self.name
