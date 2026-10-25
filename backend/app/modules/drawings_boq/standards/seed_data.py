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
  dict(
    code="LOAD_BEARING_MASONRY_A",
    name="Load-bearing masonry (illustrative)",
    description="Illustrative convention for load-bearing brick buildings: masonry walls own their volume, ground beams and "
      "lintels cut out of the wall, foundation walls sit on brick ballast. Replace with the convention of a real client BOQ (Q1).",
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
  ("MAS-BALLAST", "Brick ballast under foundation", "m3", "Masonry", "MASONRY"),
  ("MAS-DPC", "Damp-proof course", "m2", "Masonry", "DEFAULT"),
  ("FIN-PLASTER", "Cement plaster", "m2", "Finishes", "PLASTER"),
  ("FIN-PAINT", "Wall paint", "m2", "Finishes", "PAINT"),
  ("FIN-FLOOR", "Floor finish", "m2", "Finishes", "TILING"),
  ("FRM-STRUCT", "Formwork to structural concrete", "m2", "Formwork", "FORMWORK"),
  ("EXC-FOUND", "Excavation for foundations", "m3", "Earthwork", "EARTHWORK"),
  ("EXC-BACKFILL", "Backfilling around foundations", "m3", "Earthwork", "EARTHWORK"),
  ("EXC-FILL", "Earth filling under floors (compacted)", "m3", "Earthwork", "EARTHWORK"),
  ("EXC-SHORING", "Shoring to excavation", "m2", "Earthwork", "EARTHWORK"),
  ("EXC-SOIL-STAB", "Cement-stabilised compacted soil layer under foundations", "m3", "Earthwork", "EARTHWORK"),
  ("STL-REBAR", "Reinforcement steel", "kg", "Steel", "STEEL"),
  ("STL-BINDING-WIRE", "Binding wire for reinforcement", "kg", "Steel", "STEEL"),
  ("STL-CHAIRS", "Chairs and spacers for slab steel", "kg", "Steel", "STEEL"),
  ("STL-STRUCT", "Structural steel sections", "kg", "Steel", "STEEL"),
  ("STL-PILE", "Steel piles (driven length)", "m", "Piling", "DEFAULT"),
  ("PIL-BORE", "Boring of cast-in-situ piles (length bored); the concrete and the steel are billed in their own lines", "m", "Piling", "DEFAULT"),
  ("DOR-NOS", "Doors", "nos", "Joinery", "DEFAULT"),
  ("WIN-NOS", "Windows", "nos", "Joinery", "DEFAULT"),
  ("PRO-TERMITE", "Anti-termite treatment", "m2", "Protection", "DEFAULT"),
  ("FLR-KACHA-BED", "Concrete or kacha bed under the floor", "m2", "Finishes", "DEFAULT"),
  ("FLR-BALLAST", "Brick ballast under the floor", "m3", "Masonry", "DEFAULT"),
  ("FLR-SAND-FILL", "Sand filling under the floor", "m3", "Earthwork", "DEFAULT"),
  ("FIN-POLYTHENE", "Polythene sheet membrane", "m2", "Finishes", "DEFAULT"),
  ("FLR-CS-BED", "Cement-sand bed under the floor finish", "m2", "Finishes", "DEFAULT"),
  ("FLR-BRICK-TILES", "Brick tiles", "m2", "Finishes", "DEFAULT"),
  ("FLR-MUD-PLASTER", "Mud plaster", "m2", "Finishes", "DEFAULT"),
  ("FLR-COMPACTED-MUD", "Compacted mud layer", "m3", "Earthwork", "DEFAULT"),
  ("FIN-ROOF-TREAT", "Roof treatment (area of the roof)", "m2", "Finishes", "DEFAULT"),
  ("FIN-ROOF-MEMBRANE", "Roof waterproofing membrane", "m2", "Finishes", "DEFAULT"),
  ("FIN-ROOF-COBA", "Roof coba (brick-bat fill, average thickness)", "m3", "Finishes", "DEFAULT"),
  ("FIN-ROOF-SCREED", "Cement screed over the roof coba", "m2", "Finishes", "DEFAULT"),
  ("JOI-DOOR-FRAME", "Door frames (area of the frame)", "m2", "Joinery", "DEFAULT"),
  ("JOI-DOOR-AREA", "Doors (area of the openings)", "m2", "Joinery", "DEFAULT"),
  ("JOI-WIN-AREA", "Windows and ventilators (area of the openings)", "m2", "Joinery", "DEFAULT"),
  ("SCF-EXTERNAL", "External scaffolding to the outside walls above the threshold height", "m2", "Scaffolding", "DEFAULT"),
  ("FRM-PROPS", "Props under slabs above the threshold clear height", "m2", "Formwork", "FORMWORK"),
  ("FRM-ARCH", "Centring to arched openings (soffit girth times wall thickness)", "m2", "Formwork", "FORMWORK"),
  ("DRN-RWP", "Rain water pipe (down pipe) from the roof to the ground", "m", "Plumbing", "DEFAULT"),
  ("DRN-SEWER", "Sewer pipe line", "m", "Plumbing", "DEFAULT"),
  ("DRN-MANHOLE", "Manhole on the drainage line", "nos", "Plumbing", "DEFAULT"),
  ("DRN-CHAMBER", "Inspection chamber on the drainage line", "nos", "Plumbing", "DEFAULT"),
  ("DRN-GULLY", "Gully trap on the drainage line", "nos", "Plumbing", "DEFAULT"),
  ("ELE-LIGHT", "Electrical light fitting, supply and fix, counted from the plan legend", "nos", "Electrical", "DEFAULT"),
  ("ELE-FAN", "Electrical fan point, ceiling or wall fan or exhaust fan, supply and fix", "nos", "Electrical", "DEFAULT"),
  ("ELE-SOCKET", "Electrical socket or plug point, supply and fix", "nos", "Electrical", "DEFAULT"),
  ("ELE-SWITCH", "Electrical switch or switch plate, supply and fix", "nos", "Electrical", "DEFAULT"),
  ("ELE-LOWV", "Telephone, TV, data, alarm, camera and bell points, supply and fix", "nos", "Electrical", "DEFAULT"),
  ("ELE-BOARD", "Distribution board, earth set, UPS or generator, supply and fix", "nos", "Electrical", "DEFAULT"),
  ("ELE-OTHER", "Other electrical point counted from the plan legend", "nos", "Electrical", "DEFAULT"),
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
  dict(code="PUNJAB_CSR_MASONRY", name="Punjab - CSR, load-bearing masonry (draft profile)", jurisdiction="PK", province="Punjab",
    standard_name="CSR", full=True, convention="LOAD_BEARING_MASONRY_A",
    preferred_units={"volume": "cft", "area": "sft", "length": "rft", "weight": "kg", "count": "nos"},
    description="System profile for load-bearing brick buildings in Punjab. All values are placeholders pending QS sign-off."),
  dict(code="GENERIC_METRIC", name="Generic metric (fallback)", jurisdiction=None, province=None,
    standard_name=None, full=False, description="Minimal fallback profile."),
]