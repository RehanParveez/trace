"""
Configuration for which IFC element types are extracted into BOQ lines,
and the quantity-property lookup order used per type. Kept as data, not
scattered through extraction logic, so expanding this list later is a
one-line change -- matches "prefer configuration over hard-coding" from
the improvement roadmap.
"""
from __future__ import annotations

TARGET_IFC_TYPES: list[str] = [
  "IfcWall",
  "IfcWallStandardCase",
  "IfcSlab",
  "IfcBeam",
  "IfcColumn",
  "IfcDoor",
  "IfcWindow",
  "IfcRoof",
  "IfcStair",
  "IfcStairFlight",
  "IfcRamp",
  "IfcRampFlight",
  "IfcRailing",
  "IfcFooting",
  "IfcPile",
  "IfcMember",
  "IfcPlate",
  "IfcCovering",
  "IfcCurtainWall",
  "IfcPipeSegment",
  "IfcFlowTerminal",
  "IfcFurnishingElement",
  "IfcBuildingElementProxy",
]

OPTIONAL_IFC4X3_INFRASTRUCTURE_TYPES: list[str] = [
  "IfcEarthworksCut",
  "IfcEarthworksFill",
  "IfcPavement",
  "IfcKerb",
]

QUANTITY_LOOKUP_ORDER: list[tuple[list[str], str]] = [
  (["NetVolume", "GrossVolume"], "m3"),
  (["NetArea", "GrossArea"], "m2"),
  (["Length"], "m"),
]