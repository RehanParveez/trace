from app.core.exceptions import TraceException

def require_permission(allowed: bool) -> None:
  if not allowed:
    raise TraceException("You do not have permission for this action.", 403, "FORBIDDEN")