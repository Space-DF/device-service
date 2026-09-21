import django.db.models.deletion
from django.db import migrations, models


def copy_trip_device(apps, schema_editor):
    Trip = apps.get_model("device", "Trip")
    for trip in Trip.objects.select_related("space_device").all():
        trip.device_id = trip.space_device.device_id
        trip.save(update_fields=["device"])


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0021_move_network_server_claim_code_and_add_api_device"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="device",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="device.device",
            ),
        ),
        migrations.RunPython(copy_trip_device, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="trip",
            name="device",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="device.device",
            ),
        ),
        migrations.RemoveField(
            model_name="trip",
            name="space_device",
        ),
    ]
