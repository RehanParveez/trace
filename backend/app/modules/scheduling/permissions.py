from app.modules.identity.enums import PermissionKey

SCHEDULING_PERMISSIONS = {
  PermissionKey.SCHEDULE_READ: "View the project schedule, timeline and critical path.",
  PermissionKey.SCHEDULE_MANAGE: "Create and edit schedule tasks, dependencies and target dates.",
}