"""Run the device downgrade consumer."""
from common.utils.downgrade_consumer import run_downgrade_consumer
from django.core.management.base import BaseCommand

from apps.device.consumers import deactivate_excess_devices


class Command(BaseCommand):
    help = "Listen for org.downgraded events and deactivate excess devices."

    def handle(self, *args, **options):
        self.stdout.write("Starting device downgrade consumer...")
        run_downgrade_consumer(
            queue_name="device.org.events.queue",
            callback=deactivate_excess_devices,
        )
