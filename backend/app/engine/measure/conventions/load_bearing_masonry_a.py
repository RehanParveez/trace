from __future__ import annotations
from app.engine.measure.conventions.frame_monolithic_a import FrameMonolithicA

_RANKS = {
  "COLUMN": 10,
  "WALL_SHEAR": 20, "WALL_RETAINING": 22,
  "SLAB": 30, "SLAB_FOUNDATION": 30, "SLAB_ROOF": 30, "SLAB_LANDING": 30,
  "FOOTING": 40, "PILE": 45,
  "BEAM": 50, "EDGE_BEAM": 50, "GIRDER_SEGMENT": 50, "DIAPHRAGM": 50, "GROUND_BEAM": 50, "PLINTH_BEAM": 50,
  "LINTEL": 55,
  "WALL_FOUNDATION": 85,
  "WALL": 90, "WALL_EXTERNAL": 90, "WALL_LOAD_BEARING": 90, "WALL_PARAPET": 90,
  "WALL_INTERNAL": 95, "WALL_PARTITION": 95,
}

class LoadBearingMasonryA(FrameMonolithicA):
  code = "LOAD_BEARING_MASONRY_A"
  conserves_volume = True

  def rank(self, role: str) -> int | None:
    return _RANKS.get(role)

  def classify(self, loser_role: str, owner_role: str) -> tuple[str, str]:
    if loser_role == "WALL_FOUNDATION" and owner_role not in ("WALL_FOUNDATION",):
      return "OVERLAP_ALLOCATION", f"foundation_wall.{owner_role.lower()}.higher_rank_owns"
    if loser_role in ("GROUND_BEAM", "PLINTH_BEAM") and owner_role == "COLUMN":
      return "EXTENT_TRIMMING", "beam.column_face_to_face"
    return super().classify(loser_role, owner_role)