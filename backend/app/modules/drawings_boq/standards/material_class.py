from __future__ import annotations

_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (

  (("rcc", "pcc", "concrete", "cement concrete", "reinforced concrete", "reinforced cement concrete", "plain concrete", "plain cement concrete",
    "ready mix concrete", "ready-mix concrete", "rmc", "lean concrete", "blinding concrete", "mass concrete", "precast concrete", "prestressed concrete", 
    "post tensioned concrete", "post-tensioned concrete", "shotcrete", "sprayed concrete", "ferrocement", "m15", "m20", "m25",
    "m30", "m35", "m40", "m45", "m50"), "CONCRETE"),

  (("brick", "brickwork", "brick wall", "brick masonry", "clay brick", "burnt clay brick", "common brick", "engineering brick", "block", "blockwork",
    "block wall", "block masonry", "concrete block", "concrete blocks", "hollow block", "hollow blocks", "solid block", "solid blocks", "solid concrete block",
    "hollow concrete block", "cmu", "aac block", "aac blocks", "autoclaved aerated concrete", "lightweight block", "lightweight blocks", "fly ash block",
    "cement block", "sand cement block", "stone masonry", "stone wall", "rubble masonry", "random rubble", "coursed rubble", "ashlar masonry",
    "dry stone masonry", "masonry"), "MASONRY"),

  (("rebar", "reinforcement", "reinforcing bar", "reinforcing bars", "reinforcement bar", "reinforcement bars", "reinforcing steel", "reinforcement steel",
    "deformed bar", "deformed bars", "ribbed bar", "ribbed bars", "tmt bar", "tmt bars", "tor steel", "tor bars", "high yield steel", 
    "high yield deformed bar", "hysd", "hy grade steel", "steel reinforcement", "rebar steel", "steel bar reinforcement"), "REINFORCEMENT"),

  (("rebar mesh", "reinforcement mesh", "steel mesh", "welded wire mesh", "welded mesh", "wire mesh", "welded wire fabric", "wwf", "brc mesh",
    "brc fabric", "reinforcing mesh", "steel fabric"), "REINFORCEMENT_MESH"),

  (("structural steel", "structural steelwork", "steel structure", "steel framing", "steel frame", "steel beam", "steel column", "i beam",
    "i-beam", "h beam", "h-beam", "universal beam", "universal column", "ub", "uc", "channel", "c channel", "steel channel", "angle", "steel angle", 
    "equal angle", "unequal angle", "flat bar", "flat steel", "steel plate", "steel sheet", "steel joist", "steel truss", "steel purlin",
    "purlin", "z purlin", "c purlin", "steel decking", "metal decking", "deck sheet", "chequered plate", "mild steel", "ms steel"), "STRUCTURAL_STEEL"),

  (("plaster", "cement plaster", "cement render", "cement rendering", "sand cement plaster", "sand cement render", "internal plaster",
    "external plaster", "wall plaster", "ceiling plaster", "render", "rendering", "stucco", "gypsum plaster", "gypsum render",
    "lime plaster", "lime render", "skim coat", "wall skim", "wall putty", "mortar", "cement mortar", "sand cement mortar", "lime mortar", 
    "screed", "cement screed", "floor screed", "levelling screed", "leveling screed"), "PLASTER"),

  (("paint", "painting", "emulsion", "emulsion paint", "plastic emulsion", "acrylic paint", "acrylic coating", "distemper", "cement paint",
    "weather coat", "weatherproof coating", "exterior paint", "interior paint", "primer", "paint primer", "sealer", "undercoat", "enamel",
    "enamel paint", "synthetic enamel", "oil paint", "gloss paint", "matt paint", "matte paint", "texture paint", "textured coating",
    "epoxy coating", "epoxy paint", "polyurethane coating", "pu coating", "protective coating", "anti corrosion coating", "anticorrosive coating"), "PAINT"),

  (("tile", "tiles", "ceramic tile", "ceramic tiles", "porcelain tile", "porcelain tiles", "vitrified tile", "vitrified tiles", "glazed tile", 
    "glazed tiles", "unglazed tile", "mosaic", "mosaic tile", "marble", "marble tile", "granite", "granite tile", "travertine", "limestone", 
    "sandstone", "slate", "terrazzo", "kota stone", "kota", "natural stone", "stone cladding", "wall tile", "floor tile", "tile adhesive", "tile grout",
    "grout"), "TILING"),

  (("timber", "wood", "wooden", "hardwood", "softwood", "plywood", "marine plywood", "commercial plywood", "mdf", "hdf", "particle board", "chipboard",
    "blockboard", "veneer", "wood veneer", "laminated board", "melamine board", "timber door", "wooden door", "timber frame", "wooden frame",
    "timber skirting", "wood skirting", "carpentry", "joinery"), "TIMBER"),

  (("waterproofing", "waterproof", "water proofing", "damp proofing", "dpc", "dpm", "damp proof course", "damp proof membrane", "waterproof membrane",
    "bituminous membrane", "bitumen membrane", "torch on membrane", "torch-on membrane", "app membrane", "sbs membrane", "liquid waterproofing", 
    "cementitious waterproofing", "crystalline waterproofing", "polyurethane waterproofing", "pu waterproofing", "epoxy waterproofing", "waterstop", 
    "water bar", "bentonite waterproofing"), "WATERPROOFING"),

  (("earthwork", "earth works", "excavation", "excavated soil", "soil", "earth", "fill", "filling", "backfill", "back filling", "selected fill", 
    "approved fill", "granular fill", "sand fill", "compacted fill", "embankment", "subgrade", "sub-grade", "hardcore", "hard core", "soling", 
    "stone soling"), "EARTHWORK"),

  (("aggregate", "aggregates", "coarse aggregate", "fine aggregate", "crush", "crushed stone", "crushed aggregate", "stone aggregate", "gravel",
    "shingle", "sand", "river sand", "natural sand", "crushed sand", "manufactured sand", "m sand", "screenings", "stone dust", "10mm aggregate",
    "20mm aggregate", "25mm aggregate", "40mm aggregate", "10 mm aggregate", "20 mm aggregate", "25 mm aggregate", "40 mm aggregate"), "AGGREGATE"),

  (("cement", "opc", "ordinary portland cement", "portland cement", "ppc", "portland pozzolana cement", "src", "sulphate resisting cement",
    "sulfate resisting cement", "rapid hardening cement", "white cement", "hydraulic cement", "lime", "quicklime", "hydrated lime", "gypsum",
    "cementitious binder", "binder"), "CEMENT_BINDER"),

  (("glass", "glazing", "clear glass", "float glass", "toughened glass", "tempered glass", "laminated glass", "double glazing", "double glazed",
    "insulated glass", "igu", "low e glass", "low-e glass", "frosted glass", "obscure glass", "wired glass", "mirror", "mirrored glass"), "GLASS"),

  (("aluminium", "aluminum", "aluminium frame", "aluminum frame", "aluminium section", "aluminum section", "aluminium window", "aluminum window",
    "aluminium door", "aluminum door", "curtain wall", "storefront", "metal fabrication", "sheet metal", "galvanized steel", "galvanised steel",
    "gi sheet", "galvanized iron", "galvanised iron", "flashing", "metal louver", "metal louvers", "louvre", "louver",
    "metal railing", "metal handrail"), "METAL_FABRICATION"),

  (("roofing", "roof sheet", "roof sheets", "metal roofing", "gi roofing", "gi sheet roofing", "corrugated sheet", "corrugated roofing", 
    "standing seam", "standing seam roofing", "metal roof", "roof tile", "roof tiles", "clay roof tile", "concrete roof tile", "asphalt shingle",
    "roof membrane", "roof covering"), "ROOFING"),

  (("insulation", "thermal insulation", "acoustic insulation", "sound insulation", "eps", "expanded polystyrene", "xps", 
    "extruded polystyrene", "pu foam", "polyurethane foam", "pir insulation", "rock wool", "rockwool", "mineral wool", "glass wool",
    "fiberglass insulation", "insulation board"), "INSULATION"),

  (("false ceiling", "suspended ceiling", "gypsum ceiling", "gypsum board ceiling", "gypsum board", "plasterboard", "ceiling board", 
    "ceiling tile", "acoustic ceiling", "metal ceiling", "metal ceiling tile", "t grid", "exposed grid", "suspended grid"), "CEILING"),
)

_ROLE_DEFAULTS: dict[str, str] = {

  "COLUMN": "CONCRETE", "COLUMN_STRUCTURAL": "CONCRETE", "COLUMN_PRECAST": "CONCRETE",
  "BEAM": "CONCRETE", "BEAM_STRUCTURAL": "CONCRETE", "BEAM_EDGE": "CONCRETE", "BEAM_TRANSFER": "CONCRETE", "BEAM_PRECAST": "CONCRETE",
  "SLAB": "CONCRETE", "SLAB_STRUCTURAL": "CONCRETE", "SLAB_ROOF": "CONCRETE", "SLAB_GROUND": "CONCRETE", "SLAB_FOUNDATION": "CONCRETE", "SLAB_PRECAST": "CONCRETE",
  "SLAB_POST_TENSIONED": "CONCRETE", "FOUNDATION": "CONCRETE", "FOOTING": "CONCRETE", "FOOTING_ISOLATED": "CONCRETE", "FOOTING_STRIP": "CONCRETE", 
  "FOOTING_COMBINED": "CONCRETE", "RAFT": "CONCRETE", "RAFT_FOUNDATION": "CONCRETE", "PILE": "CONCRETE", "PILE_FOUNDATION": "CONCRETE",
  "PILE_CAP": "CONCRETE", "GROUND_BEAM": "CONCRETE", "WALL": "MASONRY", "WALL_EXTERNAL": "MASONRY", "WALL_INTERNAL": "MASONRY", "WALL_PARTITION": "MASONRY", 
  "WALL_LOAD_BEARING": "MASONRY", "WALL_FOUNDATION": "MASONRY", "WALL_RETAINING": "CONCRETE", "WALL_SHEAR": "CONCRETE", "WALL_CORE": "CONCRETE",
  "LINTEL": "CONCRETE", "SILL": "CONCRETE", "PARAPET": "MASONRY", "KERB": "CONCRETE",
  "STAIR": "CONCRETE", "STAIR_FLIGHT": "CONCRETE", "LANDING": "CONCRETE", "RAMP": "CONCRETE", "RAMP_SLAB": "CONCRETE",
  "REBAR": "REINFORCEMENT", "REBAR_MESH": "REINFORCEMENT_MESH", "REBAR_STIRRUP": "REINFORCEMENT", "REBAR_TIE": "REINFORCEMENT", "REBAR_DOWEL": "REINFORCEMENT",
  "FORMWORK": "FORMWORK", "ROOF": "ROOFING", "ROOF_STRUCTURE": "STRUCTURAL_STEEL", "CURTAIN_WALL": "METAL_FABRICATION", "GLAZING": "GLASS",
  "WINDOW": "METAL_FABRICATION", "DOOR": "TIMBER",
  "CEILING": "CEILING",
}

def classify_material_class(
  *,
  mapping_material_class: str | None = None,
  work_item_material_class: str | None = None,
  material_text: str | None = None,
  structural_role: str | None = None,
) -> str:
  """Order: explicit mapping -> work-item catalog -> keywords in material text -> role -> DEFAULT."""
  if mapping_material_class:
    return mapping_material_class.upper()
  if work_item_material_class:
    return work_item_material_class.upper()
  text = (material_text or "").lower()
  for words, cls in _KEYWORDS:
    if any(w in text for w in words):
      return cls
  if structural_role and structural_role in _ROLE_DEFAULTS:
    return _ROLE_DEFAULTS[structural_role]
  return "DEFAULT"