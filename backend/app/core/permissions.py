from enum import StrEnum


class Permission(StrEnum):
    VIEW_WORKFLOWS = "view_workflows"
    EDIT_WORKFLOWS = "edit_workflows"
    RUN_WORKFLOWS = "run_workflows"
    RUN_BROWSER_NODES = "run_browser_nodes"
    RUN_CLI_NODES = "run_cli_nodes"
    RUN_PRIVILEGED_CLI_NODES = "run_privileged_cli_nodes"
    MANAGE_AGENTS = "manage_agents"
    MANAGE_SECRETS = "manage_secrets"
    APPROVE_HEALED_LOCATORS = "approve_healed_locators"
    CREATE_WORKBOARD_DEFECTS = "create_workboard_defects"
    MANAGE_USERS = "manage_users"
    MANAGE_SSO = "manage_sso"
    MANAGE_API_KEYS = "manage_api_keys"
    EXPOSE_WORKFLOWS = "expose_workflows"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "owner": set(Permission),
    "admin": set(Permission),
    "member": {
        Permission.VIEW_WORKFLOWS,
        Permission.EDIT_WORKFLOWS,
        Permission.RUN_WORKFLOWS,
        Permission.RUN_BROWSER_NODES,
        Permission.RUN_CLI_NODES,
        Permission.CREATE_WORKBOARD_DEFECTS,
        Permission.EXPOSE_WORKFLOWS,
    },
    "viewer": {Permission.VIEW_WORKFLOWS},
}

VALID_ROLES = ("owner", "admin", "member", "viewer")


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def permissions_for_role(role: str) -> list[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, set()))
