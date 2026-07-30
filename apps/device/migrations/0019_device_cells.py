from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0018_device_deactivated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="cells",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
