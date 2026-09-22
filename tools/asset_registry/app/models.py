from django.db import models


class Asset(models.Model):
    name = models.CharField(max_length=200)
    did = models.CharField(max_length=500, unique=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.name
