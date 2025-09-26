from django.db import migrations


def create_connector_default(apps, schema_editor):
    pass


def delete_connector_default(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0003_alter_lorawandevice_device"),
    ]

    operations = [
        migrations.RunPython(create_connector_default, delete_connector_default),
    ]
