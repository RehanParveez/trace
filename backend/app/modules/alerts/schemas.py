from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel

class AttentionItemResponse(BaseModel):
  kind: str
  count: int
  amount: Decimal | None = None

class AttentionResponse(BaseModel):
  currency: str
  items: list[AttentionItemResponse]