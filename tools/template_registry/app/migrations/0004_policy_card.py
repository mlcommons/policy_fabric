from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0003_policy_components"),
    ]

    operations = [
        migrations.RenameField(model_name="policytemplate", old_name="readme", new_name="policy_card"),
    ]
