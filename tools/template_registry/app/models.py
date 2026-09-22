from django.db import models


class PolicyTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    policy_data_schema = models.JSONField(default=dict)
    rego_source = models.TextField(default="")
    readme = models.TextField(default="")

    def __str__(self):
        return self.name


class CredentialTemplate(models.Model):
    template_type = models.CharField(max_length=100, unique=True)
    claims_schema = models.JSONField(default=dict)

    def __str__(self):
        return self.template_type
