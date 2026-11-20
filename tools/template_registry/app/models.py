from django.db import models


class PolicyTemplate(models.Model):
    """A policy card: a graph of policy components, ending in the grant of one kind of
    guardian."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=40, default="")
    title = models.CharField(max_length=200, default="")
    rule = models.TextField(default="")
    # the guardians the card's grant fits: download or inference
    guardian_types = models.JSONField(default=list)
    # its policy_card.md, the full Policy Card
    policy_card = models.TextField(default="")
    # the card, its graph.json
    graph = models.JSONField()

    def __str__(self):
        return self.name


class PolicyComponent(models.Model):
    """A policy component: Rego that the nodes of a policy graph run."""

    component_id = models.CharField(max_length=100, unique=True)
    package = models.CharField(max_length=200)
    rego_source = models.TextField()
    # its component.json: name, group, summary, inputs, output and policy data, as shown
    metadata = models.JSONField()
    # JSON Schema of a node's policy data; it generates the owner's form
    policy_data_schema = models.JSONField()

    def __str__(self):
        return self.component_id


class CredentialTemplate(models.Model):
    """A credential type, presented to policy components or produced by them."""

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
    # whether a wallet may present it, so an authority may issue it: a type no policy
    # component produces, or a produced type whose schema says x-presentable
    presentable = models.BooleanField(default=True)
    # a flat fill-in hint derived from json_schema
    claims_schema = models.JSONField(default=dict)

    def __str__(self):
        return self.template_type
