from __future__ import annotations

class Convention:
  code: str = ""
  conserves_volume: bool = True

  def rank(self, role: str) -> int | None:
    raise NotImplementedError

  def classify(self, loser_role: str, owner_role: str) -> tuple[str, str]:
    raise NotImplementedError