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
    },
    "viewer": {Permission.VIEW_WORKFLOWS},
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
