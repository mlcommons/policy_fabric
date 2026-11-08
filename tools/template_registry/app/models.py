from django.db import models


class PolicyTemplate(models.Model):
    """A policy card, or the delivery module of a guardian type."""

    POLICY = "policy"
    DELIVERY = "delivery"

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=20, default=POLICY)
    code = models.CharField(max_length=40, default="")
    title = models.CharField(max_length=200, default="")
    rule = models.TextField(default="")
    guardian_types = models.JSONField(default=list)
    # the facts the module reads: { role: [credential_type, ...] }
    requirements = models.JSONField(default=dict)
    # JSON Schema of the module's policy data; it generates the owner's form
    parameters_schema = models.JSONField(default=dict)
    defaults = models.JSONField(default=dict)
    operation = models.CharField(max_length=100, default="")
    rego_source = models.TextField(default="")
    readme = models.TextField(default="")

    def __str__(self):
        return self.name


class AuthorityTemplate(models.Model):
    """A rule-based authority card: a rule whose output is a credential."""

    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200, default="")
    rule = models.TextField(default="")
    issues = models.CharField(max_length=100)
    presenters = models.TextField(default="")
    requirements = models.JSONField(default=dict)
    parameters_schema = models.JSONField(default=dict)
    rego_source = models.TextField(default="")
    readme = models.TextField(default="")

    def __str__(self):
        return self.name


class CredentialTemplate(models.Model):
    """A credential type: a standard fact, or an input to an authority."""

    template_type = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200, default="")
    meaning = models.TextField(default="")
    # what the subject DID names: wallet, script, project, committee, ...
    subject_kinds = models.JSONField(default=list)
    # signed by the requester's own wallet and checked against its key, so no
    # authority is accepted for it
    self_asserted = models.BooleanField(default=False)
    # the full JSON Schema of the claims
    json_schema = models.JSONField(default=dict)
    # a flat fill-in hint derived from json_schema
    claims_schema = models.JSONField(default=dict)

    def __str__(self):
        return self.template_type
