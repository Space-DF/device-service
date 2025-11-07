from common.apps.organization_role.constants import OrganizationRoleType
from common.apps.space_role.constants import SpaceRoleType
from django.conf import settings

from utils.remote_permission import RemotePermission


# Space permission
class IsSpaceAdmin(RemotePermission):
    allowed_roles = [SpaceRoleType.ADMIN_ROLE]
    auth_url = settings.AUTH_URL
    header_name = "X-Space"


class IsSpaceEditor(RemotePermission):
    allowed_roles = [SpaceRoleType.EDITOR_ROLE, SpaceRoleType.ADMIN_ROLE]
    auth_url = settings.AUTH_URL
    header_name = "X-Space"


# Organization permission
class IsOrganizationOwner(RemotePermission):
    allowed_roles = [OrganizationRoleType.OWNER_ROLE]
    auth_url = settings.CONSOLE_AUTH_URL
    header_name = "X-Organization"


class IsOrganizationAdmin(RemotePermission):
    allowed_roles = [OrganizationRoleType.ADMIN_ROLE, OrganizationRoleType.OWNER_ROLE]
    auth_url = settings.CONSOLE_AUTH_URL
    header_name = "X-Organization"


class IsOrganizationEditor(RemotePermission):
    allowed_roles = [
        OrganizationRoleType.EDITOR_ROLE,
        OrganizationRoleType.ADMIN_ROLE,
        OrganizationRoleType.OWNER_ROLE,
    ]
    auth_url = settings.CONSOLE_AUTH_URL
    header_name = "X-Organization"
