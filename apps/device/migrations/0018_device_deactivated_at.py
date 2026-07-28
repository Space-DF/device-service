from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0017_device_is_deactivated"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="deactivated_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
