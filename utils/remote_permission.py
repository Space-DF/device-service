from urllib.parse import urlsplit

import requests
from rest_framework.permissions import BasePermission


class RemotePermission(BasePermission):
    allowed_roles = []
    auth_url = None
    error_message = "You do not have permission."

    def has_permission(self, request, view):
        user_id = request.headers.get("X-User-ID")
        slug_name = request.headers.get(self.header_name)
        headers = {}

        if self.header_name == "X-Space":
            domain = urlsplit(request.build_absolute_uri()).hostname
            headers = {"Host": domain}

        if not user_id or not slug_name or not self.auth_url:
            return False

        data = {
            "user_id": user_id,
            "slug_name": slug_name,
            "allowed_roles": self.allowed_roles,
        }

        try:
            resp = requests.post(self.auth_url, json=data, headers=headers, timeout=2)
            resp.raise_for_status()
            return resp.json().get("allowed", False)
        except requests.RequestException:
            return False
