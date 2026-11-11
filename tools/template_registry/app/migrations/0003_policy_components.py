from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_cards"),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyComponent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("component_id", models.CharField(max_length=100, unique=True)),
                ("package", models.CharField(max_length=200)),
                ("rego_source", models.TextField()),
                ("metadata", models.JSONField()),
                ("policy_data_schema", models.JSONField()),
            ],
        ),
        migrations.DeleteModel(name="AuthorityTemplate"),
        migrations.RemoveField(model_name="policytemplate", name="kind"),
        migrations.RemoveField(model_name="policytemplate", name="requirements"),
        migrations.RemoveField(model_name="policytemplate", name="parameters_schema"),
        migrations.RemoveField(model_name="policytemplate", name="defaults"),
        migrations.RemoveField(model_name="policytemplate", name="operation"),
        migrations.RemoveField(model_name="policytemplate", name="rego_source"),
        migrations.AddField(
            model_name="policytemplate",
            name="graph",
            field=models.JSONField(default=dict),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="credentialtemplate",
            name="presentable",
            field=models.BooleanField(default=True),
        ),
    ]
