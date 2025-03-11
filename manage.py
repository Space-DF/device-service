#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import importlib.util
import os
import sys

from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    load_dotenv()

    if importlib.util.find_spec("common") is None:
        sys.path.append(
            os.path.abspath(os.path.join("..", "django-common-utils"))
        )  # Import django-common-utils without install
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "device_service.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
