import secrets
import string

from apps.device.models import APIDevice


def generate_api_serial_number():
    alphabet = string.ascii_lowercase + string.digits
    while True:
        suffix = "".join(secrets.choice(alphabet) for _ in range(8))
        serial_number = f"serial-{suffix}"
        if not APIDevice.objects.filter(serial_number=serial_number).exists():
            return serial_number
