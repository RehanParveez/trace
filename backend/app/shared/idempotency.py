from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class IdempotencyContext:
  key: str
  user_id: UUID | None = None
  organization_id: UUID | None = None