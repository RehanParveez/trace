from __future__ import annotations
from pydantic import BaseModel
from uuid import UUID

class FirstRunStarted(BaseModel):
  project_id: UUID
  queued: bool
  drawings: int

class FirstRunReport(BaseModel):
  project_id: UUID
  has_ledger: bool
  snapshot_at: str | None = None
  ran_at: str | None = None
  project: dict | None = None
  scope: str | None = None
  sets_found: list = []
  items: dict = {}
  entries: int = 0
  boq: dict = {}
  questions: dict = {}
  stages: list = []
  failed: list = []
  unread: list = []
  seconds: float = 0.0
