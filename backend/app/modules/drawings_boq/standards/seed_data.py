from __future__ import annotations
from decimal import Decimal

PLACEHOLDER = "PLACEHOLDER - confirm with QS (Q7)"

CONVENTIONS = [
  dict(
    code="FRAME_MONOLITHIC_A",
    name="Framed monolithic RCC (illustrative)",
    description="Illustrative convention from architecture Appendix A. Replace with the convention of a real client BOQ (Q1).",
    conserves_volume=True,
    parameters={
      "column_extent": "full_footprint_full_height",
      "beam_extent": "column_face_to_face",
      "beam_slab_overlap": "slab_owns_top_layer",
      "slab": "reduced_by_column_footprints",
    },
  ),
]

WORK_ITEMS = [
  ("CON-RCC", "Reinforced cement concrete (structural)", "m3", "Concrete", "CONCRETE"),
  ("CON-PCC", "Plain cement concrete (blinding)", "m3", "Concrete", "CONCRETE"),
  ("MAS-BRICK", "Brick masonry", "m3", "Masonry", "MASONRY"),
  ("FIN-PLASTER", "Cement plaster", "m2", "Finishes", "PLASTER"),
  ("FIN-PAINT", "Wall paint", "m2", "Finishes", "PAINT"),
  ("FIN-FLOOR", "Floor finish", "m2", "Finishes", "TILING"),
  ("FRM-STRUCT", "Formwork to structural concrete", "m2", "Formwork", "FORMWORK"),
  ("EXC-FOUND", "Excavation for foundations", "m3", "Earthwork", "EARTHWORK"),
  ("STL-REBAR", "Reinforcement steel", "kg", "Steel", "STEEL"),
  ("DOR-NOS", "Doors", "nos", "Joinery", "DEFAULT"),
  ("WIN-NOS", "Windows", "nos", "Joinery", "DEFAULT"),
]

MAPPINGS = [
  ("IfcColumn", "CON-RCC", "Concrete", "CONCRETE"),
  ("IfcBeam", "CON-RCC", "Concrete", "CONCRETE"),
  ("IfcSlab", "CON-RCC", "Concrete", "CONCRETE"),
  ("IfcFooting", "CON-RCC", "Concrete", "CONCRETE"),
  ("IfcWall", "MAS-BRICK", "Masonry", "MASONRY"),
  ("IfcWallStandardCase", "MAS-BRICK", "Masonry", "MASONRY"),
  ("IfcDoor", "DOR-NOS", "Doors", "DEFAULT"),
  ("IfcWindow", "WIN-NOS", "Windows", "DEFAULT"),
]

OPENING_THRESHOLD_M2 = Decimal("0.5") 
WASTAGE_FULL = [("CONCRETE", "1.02"), ("MASONRY", "1.05"), ("STEEL", "1.03"), ("PLASTER", "1.05"),
  ("PAINT", "1.05"), ("TILING", "1.05"), ("FORMWORK", "1.00"), ("EARTHWORK", "1.00"), ("DEFAULT", "1.00")]
WASTAGE_MIN = [("DEFAULT", "1.00")]

REBAR_CANDIDATE = {"status": "CANDIDATE_UNCONFIRMED", "source": "architecture v2 s10.1 / Q5"}
REBAR_RULES = [
  dict(element_scope="ALL", bar_role="MAIN", lap_basis="diameter_multiple", lap_coefficient=Decimal("40"),
    hook_rules={"standard_hook_d_multiple": 12}, bend_rules={"deduction_d_multiple": {"45": 1, "90": 2, "135": 3}},
    dev_length_method="basic", splice_constraints={"stock_length_m": 12}, extra_config=REBAR_CANDIDATE),
  dict(element_scope="ALL", bar_role="STIRRUP", lap_basis=None, lap_coefficient=None,
    hook_rules={"stirrup_hook_d_multiple": 10}, bend_rules={"deduction_d_multiple": {"45": 1, "90": 2, "135": 3}},
    dev_length_method=None, splice_constraints={}, extra_config=REBAR_CANDIDATE),
]

RECIPES = [
  dict(code="WALL_FINISHES", name="Wall plaster and paint", triggers=["IfcWall", "IfcWallStandardCase"], components=[
    (1, "FIN-PLASTER", "Cement plaster to {material}", "m2", "WALL_FACE_AREA_NET", "Finishes", False),
    (2, "FIN-PAINT", "Paint to plastered {material}", "m2", "PAINT_AREA", "Finishes", True),
  ]),
  dict(code="STRUCT_FORMWORK", name="Structural formwork", triggers=["IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting"], components=[
    (1, "FRM-STRUCT", "Formwork to {material}", "m2", "SOLID_FORMWORK_AREA", "Formwork", False),
  ]),
  dict(code="FOOTING_PREP", name="Footing blinding and excavation", triggers=["IfcFooting"], components=[
    (1, "CON-PCC", "PCC blinding below {material}", "m3", "FOOTING_PCC_VOLUME", "Concrete", False),
    (2, "EXC-FOUND", "Excavation for {material}", "m3", "EXCAVATION_VOLUME", "Earthwork", False),
  ]),
]

PROFILES = [
  dict(code="PUNJAB_CSR", name="Punjab - CSR (draft profile)", jurisdiction="PK", province="Punjab",
    standard_name="CSR", full=True,
    preferred_units={"volume": "cft", "area": "sft", "length": "rft", "weight": "kg", "count": "nos"},
    description="System profile for Punjab. All values are placeholders pending QS sign-off."),
  dict(code="GENERIC_METRIC", name="Generic metric (fallback)", jurisdiction=None, province=None,
    standard_name=None, full=False, description="Minimal fallback profile."),
]