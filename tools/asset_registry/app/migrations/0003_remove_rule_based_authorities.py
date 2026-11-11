from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_directory"),
    ]

    operations = [
        migrations.RemoveField(model_name="authority", name="inputs"),
        migrations.RemoveField(model_name="authority", name="sources"),
    ]
