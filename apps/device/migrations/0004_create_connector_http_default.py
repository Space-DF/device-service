from django.db import migrations
from apps.device.services import create_connector_http, delete_connector_http


def create_connector_default(apps, schema_editor):
    create_connector_http("connector_http_default")


def delete_connector_default(apps, schema_editor):
    delete_connector_http("connector_http_default")


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0003_alter_lorawandevice_device"),
    ]

    operations = [
        migrations.RunPython(create_connector_default, delete_connector_default),
    ]
