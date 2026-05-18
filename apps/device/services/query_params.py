from uuid import UUID

from rest_framework.exceptions import ParseError


def parse_uuid_query_param(raw_value, param_name):
    if raw_value is None:
        return []

    values = []
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue

        try:
            values.append(UUID(item))
        except ValueError as exc:
            raise ParseError(f"Invalid UUID in '{param_name}': {item}") from exc

    return values
