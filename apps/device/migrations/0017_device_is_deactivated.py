# Generated manually — adds is_deactivated field to Device model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("device", "0016_alter_spacedevice_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="is_deactivated",
            field=models.BooleanField(default=False),
        ),
    ]
