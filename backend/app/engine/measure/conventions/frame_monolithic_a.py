from __future__ import annotations
from app.engine.measure.conventions.base import Convention

_RANKS = {
  "COLUMN": 10,
  "WALL_SHEAR": 20, "WALL_RETAINING": 22,
  "SLAB": 30, "SLAB_FOUNDATION": 30, "SLAB_ROOF": 30, "SLAB_LANDING": 30,
  "FOOTING": 40, "PILE": 45,
  "BEAM": 50, "EDGE_BEAM": 50, "GIRDER_SEGMENT": 50, "DIAPHRAGM": 50, "LINTEL": 55,
  "WALL": 90, "WALL_EXTERNAL": 90, "WALL_INTERNAL": 90, "WALL_PARAPET": 90,
}
_BEAMS = frozenset({"BEAM", "EDGE_BEAM", "GIRDER_SEGMENT", "DIAPHRAGM", "LINTEL"})
_SLABS = frozenset({"SLAB", "SLAB_FOUNDATION", "SLAB_ROOF", "SLAB_LANDING"})
_MASONRY = frozenset({"WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_PARAPET"})

class FrameMonolithicA(Convention):
  code = "FRAME_MONOLITHIC_A"
  conserves_volume = True

  def rank(self, role: str) -> int | None:
    return _RANKS.get(role)

  def classify(self, loser_role: str, owner_role: str) -> tuple[str, str]:
    if loser_role == owner_role:
      return "OVERLAP_ALLOCATION", "same_role.lowest_id_owns"
    if loser_role in _BEAMS and owner_role == "COLUMN":
      return "EXTENT_TRIMMING", "beam.column_face_to_face"
    if loser_role in _BEAMS and owner_role in _SLABS:
      return "OVERLAP_ALLOCATION", "beam.web_below_slab"
    if loser_role in _SLABS and owner_role == "COLUMN":
      return "OVERLAP_ALLOCATION", "slab.column_footprint_credited_to_column"
    if loser_role in _MASONRY:
      return "OVERLAP_ALLOCATION", "wall.intrusion_deducted"
    return "OVERLAP_ALLOCATION", f"{loser_role.lower()}.{owner_role.lower()}.higher_rank_owns"