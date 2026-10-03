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
    "IfcShadingDevice",
    "IfcChimney",
    "IfcBuildingElementPart",
    "IfcBuildingElementProxy",
    "IfcFurniture",
    "IfcSystemFurnitureElement",
    "IfcFurnishingElement",
    "IfcTransportElement",
    "IfcProjectionElement",

    "IfcCaissonFoundation",
    "IfcDeepFoundation",
    "IfcBearing",
    "IfcReinforcingBar",
    "IfcReinforcingMesh",
    "IfcTendon",
    "IfcTendonAnchor",
    "IfcTendonConduit",
    "IfcReinforcingElement",
    "IfcMechanicalFastener",
    "IfcFastener",
    "IfcDiscreteAccessory",
    "IfcVibrationIsolator",
    "IfcElementAssembly",
    "IfcElementComponent",

    "IfcEarthworksElement",
    "IfcEarthworksCut",
    "IfcEarthworksFill",
    "IfcReinforcedSoil",
    "IfcPavement",
    "IfcCourse",
    "IfcKerb",
    "IfcRail",
    "IfcTrackElement",
    "IfcSign",
    "IfcSignal",
    "IfcMooringDevice",
    "IfcNavigationElement",
    "IfcGeotechnicalElement",
    "IfcGeographicElement",
    "IfcCivilElement",

    "IfcDistributionElement",
    "IfcDistributionFlowElement",
    "IfcDistributionControlElement",
    "IfcDistributionChamberElement",
    "IfcDistributionCircuit",
    "IfcFlowSegment",
    "IfcFlowFitting",
    "IfcFlowController",
    "IfcFlowMovingDevice",
    "IfcFlowStorageDevice",
    "IfcFlowTreatmentDevice",
    "IfcFlowTerminal",
    "IfcEnergyConversionDevice",

    "IfcCableCarrierSegment",
    "IfcCableCarrierFitting",
    "IfcCableSegment",
    "IfcCableFitting",
    "IfcElectricDistributionBoard",
    "IfcElectricDistributionPoint",
    "IfcElectricFlowStorageDevice",
    "IfcElectricGenerator",
    "IfcElectricMotor",
    "IfcMotorConnection",
    "IfcElectricTimeControl",
    "IfcElectricAppliance",
    "IfcJunctionBox",
    "IfcLamp",
    "IfcLightFixture",
    "IfcOutlet",
    "IfcProtectiveDevice",
    "IfcProtectiveDeviceTrippingUnit",
    "IfcSwitchingDevice",
    "IfcTransformer",
    "IfcSolarDevice",

    "IfcPipeSegment",
    "IfcPipeFitting",
    "IfcValve",
    "IfcPump",
    "IfcTank",
    "IfcSanitaryTerminal",
    "IfcWasteTerminal",
    "IfcStackTerminal",
    "IfcInterceptor",
    "IfcFlowMeter",
    "IfcDistributionChamberElement",
    "IfcMedicalDevice",

    "IfcDuctSegment",
    "IfcDuctFitting",
    "IfcDuctSilencer",
    "IfcAirTerminal",
    "IfcAirTerminalBox",
    "IfcDamper",
    "IfcFan",
    "IfcFilter",
    "IfcCoil",
    "IfcChiller",
    "IfcCondenser",
    "IfcCooledBeam",
    "IfcCoolingTower",
    "IfcEvaporativeCooler",
    "IfcEvaporator",
    "IfcHeatExchanger",
    "IfcTubeBundle",
    "IfcHumidifier",
    "IfcBoiler",
    "IfcBurner",
    "IfcCompressor",
    "IfcUnitaryEquipment",
    "IfcSpaceHeater",
    "IfcElectricHeater",
    "IfcAirToAirHeatRecovery",
    "IfcEngine",

    "IfcFireSuppressionTerminal",
    "IfcAlarm",

    "IfcAudioVisualAppliance",
    "IfcCommunicationsAppliance",
    "IfcSensor",
    "IfcActuator",
    "IfcController",
    "IfcFlowInstrument",
    "IfcUnitaryControlElement",

    "IfcConveyorSegment",

    "IfcBuiltElement",
    "IfcBuildingElement",
    "IfcElement",
]

OPTIONAL_IFC4X3_INFRASTRUCTURE_TYPES: list[str] = [
  "IfcEarthworksElement",
  "IfcEarthworksCut",
  "IfcEarthworksFill",
  "IfcReinforcedSoil",
  "IfcPavement",
  "IfcCourse",
  "IfcKerb",
  "IfcRail",
  "IfcTrackElement",
  "IfcSign",
  "IfcSignal",
  "IfcMooringDevice",
  "IfcNavigationElement",
  "IfcGeotechnicalElement",
  "IfcGeographicElement",
  "IfcCivilElement",
]

QUANTITY_LOOKUP_ORDER: list[tuple[list[str], str]] = [
  (["NetVolume", "GrossVolume"], "m3"),
  (["NetArea", "GrossArea"], "m2"),
  (["Length"], "m"),
]

READER_VERSION = "2026.10.3"
 
ROLE_BY_IFC_TYPE: dict[str, str] = {
  "IfcWall": "WALL",
  "IfcWallStandardCase": "WALL",
  "IfcSlab": "SLAB",
  "IfcBeam": "BEAM",
  "IfcColumn": "COLUMN",
  "IfcDoor": "DOOR",
  "IfcWindow": "WINDOW",
  "IfcRoof": "ROOF",
  "IfcStair": "STAIR",
  "IfcStairFlight": "STAIR",
  "IfcRamp": "RAMP",
  "IfcRampFlight": "RAMP",
  "IfcRailing": "RAILING",
  "IfcFooting": "FOOTING",
  "IfcPile": "PILE",
  "IfcMember": "MEMBER",
  "IfcPlate": "PLATE",
  "IfcCovering": "COVERING",
  "IfcCurtainWall": "CURTAIN_WALL",
  "IfcPipeSegment": "PIPE",
  "IfcFlowTerminal": "FIXTURE",
  "IfcFurnishingElement": "FURNISHING",
  "IfcBuildingElementProxy": "UNKNOWN",
}

EXCLUDED_IFC_TYPES = frozenset({
  "IfcOpeningElement",
  "IfcVoidingFeature",
  "IfcSurfaceFeature",
  "IfcVirtualElement",
})
 
PREDEFINED_TYPE_ROLE_OVERRIDES: dict[tuple[str, str], str] = {
  ("IfcSlab", "BASESLAB"): "SLAB_FOUNDATION",
  ("IfcSlab", "ROOF"): "SLAB_ROOF",
  ("IfcSlab", "LANDING"): "SLAB_LANDING",
  ("IfcSlab", "PAVING"): "SLAB_PAVING",
  ("IfcSlab", "SIDEWALK"): "SIDEWALK",

  ("IfcWall", "RETAININGWALL"): "WALL_RETAINING",
  ("IfcWall", "PARAPET"): "WALL_PARAPET",
  ("IfcWall", "SHEAR"): "WALL_SHEAR",

  ("IfcBeam", "LINTEL"): "LINTEL",
  ("IfcBeam", "GIRDER_SEGMENT"): "GIRDER_SEGMENT",
  ("IfcBeam", "EDGEBEAM"): "EDGE_BEAM",
  ("IfcBeam", "DIAPHRAGM"): "DIAPHRAGM",
  ("IfcBeam", "CORNICE"): "CORNICE",

  ("IfcCovering", "FLOORING"): "FLOOR_FINISH",
  ("IfcCovering", "CEILING"): "CEILING",
  ("IfcCovering", "CLADDING"): "CLADDING",
  ("IfcCovering", "ROOFING"): "ROOFING",
  ("IfcCovering", "INSULATION"): "INSULATION",
  ("IfcCovering", "MEMBRANE"): "MEMBRANE",
  ("IfcCovering", "MOLDING"): "MOLDING",
  ("IfcCovering", "SKIRTINGBOARD"): "SKIRTING",

  ("IfcDoor", "GATE"): "GATE",
  ("IfcDoor", "TRAPDOOR"): "TRAPDOOR",
  ("IfcDoor", "TURNSTILE"): "TURNSTILE",
  ("IfcDoor", "BOOM_BARRIER"): "BOOM_BARRIER",

  ("IfcSlab", "TRACKSLAB"): "TRACK_SLAB",
  ("IfcSlab", "WEARING"): "WEARING_SLAB",

  ("IfcTrackElement", "SLEEPER"): "TRACK_SLEEPER",
  ("IfcTrackElement", "FROG"): "TRACK_FROG",
  ("IfcTrackElement", "DERAILER"): "TRACK_DERAILER",
  ("IfcTrackElement", "BLOCKINGDEVICE"): "TRACK_BLOCKING_DEVICE",
  ("IfcTrackElement", "VEHICLESTOP"): "TRACK_VEHICLE_STOP",
}

SUPERTYPE_FALLBACK_TYPES = frozenset({
  "IfcElement",
  "IfcBuiltElement",
  "IfcBuildingElement",
  "IfcElementComponent",

  "IfcCivilElement",
  "IfcDistributionElement",
  "IfcDistributionFlowElement",
  "IfcDistributionControlElement",

  "IfcFlowSegment",
  "IfcFlowFitting",
  "IfcFlowController",
  "IfcFlowMovingDevice",
  "IfcFlowStorageDevice",
  "IfcFlowTreatmentDevice",
  "IfcFlowTerminal",
  "IfcEnergyConversionDevice",

  "IfcEarthworksElement",
  "IfcDeepFoundation",
  "IfcReinforcingElement",
})

_ROLES_BY_DISCIPLINE: dict[str, dict[str, str]] = {
  "ARCHITECTURAL": {
    "IfcWall": "WALL",
    "IfcWallStandardCase": "WALL",
    "IfcDoor": "DOOR",
    "IfcWindow": "WINDOW",
    "IfcCurtainWall": "CURTAIN_WALL",
    "IfcCovering": "COVERING",
    "IfcRailing": "RAILING",
    "IfcStair": "STAIR",
    "IfcStairFlight": "STAIR",
    "IfcRamp": "RAMP",
    "IfcRampFlight": "RAMP",
    "IfcRoof": "ROOF",
    "IfcShadingDevice": "SHADING_DEVICE",
    "IfcChimney": "CHIMNEY",
    "IfcFurniture": "FURNISHING",
    "IfcSystemFurnitureElement": "FURNISHING",
    "IfcFurnishingElement": "FURNISHING",
    "IfcTransportElement": "TRANSPORT",
    "IfcProjectionElement": "PROJECTION",
    "IfcBuildingElementPart": "BUILDING_PART",
    "IfcBuildingElementProxy": "UNKNOWN",
    "IfcBuiltElement": "BUILDING_ELEMENT_OTHER",
    "IfcBuildingElement": "BUILDING_ELEMENT_OTHER",
  },

  "STRUCTURAL": {
    "IfcSlab": "SLAB",
    "IfcBeam": "BEAM",
    "IfcColumn": "COLUMN",
    "IfcFooting": "FOOTING",
    "IfcPile": "PILE",
    "IfcCaissonFoundation": "CAISSON",
    "IfcDeepFoundation": "PILE",
    "IfcMember": "MEMBER",
    "IfcPlate": "PLATE",
    "IfcBearing": "BEARING",
    "IfcReinforcingBar": "REBAR",
    "IfcReinforcingMesh": "REBAR_MESH",
    "IfcTendon": "TENDON",
    "IfcTendonAnchor": "TENDON",
    "IfcTendonConduit": "TENDON",
    "IfcReinforcingElement": "REBAR",
    "IfcMechanicalFastener": "FASTENER",
    "IfcFastener": "FASTENER",
    "IfcDiscreteAccessory": "ACCESSORY",
    "IfcVibrationIsolator": "ACCESSORY",
    "IfcElementAssembly": "ASSEMBLY",
    "IfcElementComponent": "COMPONENT_OTHER",
  },

  "SITE_CIVIL": {
    "IfcEarthworksElement": "EARTHWORKS",
    "IfcEarthworksCut": "EARTHWORKS_CUT",
    "IfcEarthworksFill": "EARTHWORKS_FILL",
    "IfcReinforcedSoil": "REINFORCED_SOIL",
    "IfcPavement": "PAVEMENT",
    "IfcCourse": "COURSE",
    "IfcKerb": "KERB",
    "IfcRail": "RAIL",
    "IfcTrackElement": "TRACK",
    "IfcSign": "SIGN",
    "IfcSignal": "SIGNAL",
    "IfcMooringDevice": "MOORING_DEVICE",
    "IfcNavigationElement": "NAVIGATION_ELEMENT",
    "IfcGeotechnicalElement": "GEOTECHNICAL",
    "IfcGeographicElement": "LANDSCAPE",
    "IfcCivilElement": "CIVIL_OTHER",
  },

  "MEP_ELECTRICAL": {
    "IfcCableCarrierSegment": "CABLE_TRAY",
    "IfcCableCarrierFitting": "CABLE_TRAY_FITTING",
    "IfcCableSegment": "CABLE",
    "IfcCableFitting": "CABLE_FITTING",
    "IfcElectricDistributionBoard": "DISTRIBUTION_BOARD",
    "IfcElectricDistributionPoint": "DISTRIBUTION_POINT",
    "IfcElectricFlowStorageDevice": "ELECTRIC_STORAGE",
    "IfcElectricGenerator": "GENERATOR",
    "IfcElectricMotor": "MOTOR",
    "IfcMotorConnection": "MOTOR",
    "IfcElectricTimeControl": "ELECTRIC_CONTROL",
    "IfcElectricAppliance": "ELECTRIC_APPLIANCE",
    "IfcJunctionBox": "JUNCTION_BOX",
    "IfcLamp": "LAMP",
    "IfcLightFixture": "LIGHT_FIXTURE",
    "IfcOutlet": "OUTLET",
    "IfcProtectiveDevice": "PROTECTIVE_DEVICE",
    "IfcProtectiveDeviceTrippingUnit": "PROTECTIVE_DEVICE",
    "IfcSwitchingDevice": "SWITCH_DEVICE",
    "IfcTransformer": "TRANSFORMER",
    "IfcSolarDevice": "SOLAR_DEVICE",
  },

  "MEP_PLUMBING": {
    "IfcPipeSegment": "PIPE",
    "IfcPipeFitting": "PIPE_FITTING",
    "IfcValve": "VALVE",
    "IfcPump": "PUMP",
    "IfcTank": "TANK",
    "IfcSanitaryTerminal": "SANITARY_FIXTURE",
    "IfcWasteTerminal": "WASTE_TERMINAL",
    "IfcStackTerminal": "STACK_TERMINAL",
    "IfcInterceptor": "INTERCEPTOR",
    "IfcFlowMeter": "FLOW_METER",
    "IfcDistributionChamberElement": "CHAMBER",
    "IfcMedicalDevice": "MEDICAL_DEVICE",
  },

  "MEP_HVAC": {
    "IfcDuctSegment": "DUCT",
    "IfcDuctFitting": "DUCT_FITTING",
    "IfcDuctSilencer": "DUCT_SILENCER",
    "IfcAirTerminal": "AIR_TERMINAL",
    "IfcAirTerminalBox": "AIR_TERMINAL_BOX",
    "IfcDamper": "DAMPER",
    "IfcFan": "FAN",
    "IfcFilter": "FILTER",
    "IfcCoil": "COIL",
    "IfcChiller": "CHILLER",
    "IfcCondenser": "CONDENSER",
    "IfcCooledBeam": "COOLED_BEAM",
    "IfcCoolingTower": "COOLING_TOWER",
    "IfcEvaporativeCooler": "EVAPORATIVE_COOLER",
    "IfcEvaporator": "EVAPORATOR",
    "IfcHeatExchanger": "HEAT_EXCHANGER",
    "IfcTubeBundle": "HEAT_EXCHANGER",
    "IfcHumidifier": "HUMIDIFIER",
    "IfcBoiler": "BOILER",
    "IfcBurner": "BURNER",
    "IfcCompressor": "COMPRESSOR",
    "IfcUnitaryEquipment": "UNITARY_EQUIPMENT",
    "IfcSpaceHeater": "SPACE_HEATER",
    "IfcElectricHeater": "SPACE_HEATER",
    "IfcAirToAirHeatRecovery": "HEAT_RECOVERY",
    "IfcEngine": "ENGINE",
  },

  "MEP_FIRE": {
    "IfcFireSuppressionTerminal": "FIRE_TERMINAL",
    "IfcAlarm": "ALARM",
  },

  "MEP_LOWCURRENT": {
    "IfcAudioVisualAppliance": "AV_APPLIANCE",
    "IfcCommunicationsAppliance": "COMMUNICATIONS_APPLIANCE",
    "IfcSensor": "SENSOR",
    "IfcActuator": "ACTUATOR",
    "IfcController": "CONTROLLER",
    "IfcFlowInstrument": "INSTRUMENT",
    "IfcUnitaryControlElement": "CONTROL_PANEL",
  },

  "MEP_OTHER": {
    "IfcConveyorSegment": "CONVEYOR",
    "IfcFlowSegment": "MEP_SEGMENT",
    "IfcFlowFitting": "MEP_FITTING",
    "IfcFlowController": "FLOW_CONTROLLER",
    "IfcFlowMovingDevice": "MOVING_DEVICE",
    "IfcFlowStorageDevice": "STORAGE_DEVICE",
    "IfcFlowTreatmentDevice": "TREATMENT_DEVICE",
    "IfcFlowTerminal": "FIXTURE",
    "IfcEnergyConversionDevice": "EQUIPMENT",
    "IfcDistributionControlElement": "CONTROL_DEVICE",
    "IfcDistributionFlowElement": "MEP_OTHER",
    "IfcDistributionElement": "MEP_OTHER",
    "IfcDistributionCircuit": "DISTRIBUTION_CIRCUIT",
  },

  "UNKNOWN": {
    "IfcElement": "ELEMENT_OTHER",
  },
}

ROLE_BY_IFC_TYPE: dict[str, str] = {
  ifc_type: role
  for group in _ROLES_BY_DISCIPLINE.values()
  for ifc_type, role in group.items()
}
 
NAME_KEYWORD_ROLES: list[tuple[str, str]] = [
  ("column", "COLUMN"),
  ("pier", "COLUMN"),
  ("post", "COLUMN"),

  ("beam", "BEAM"),
  ("girder", "BEAM"),
  ("joist", "BEAM"),
  ("lintel", "LINTEL"),

  ("footing", "FOOTING"),
  ("foundation", "FOOTING"),
  ("raft", "SLAB_FOUNDATION"),
  ("pile", "PILE"),
  ("caisson", "CAISSON"),

  ("slab", "SLAB"),
  ("floor", "SLAB"),
  ("shear wall", "WALL_SHEAR"),
  ("retaining", "WALL_RETAINING"),
  ("parapet", "WALL_PARAPET"),
  ("curtain wall", "CURTAIN_WALL"),
  ("wall", "WALL"),

  ("roof", "ROOF"),
  ("stair", "STAIR"),
  ("step", "STAIR"),
  ("ramp", "RAMP"),
  ("railing", "RAILING"),

  ("door", "DOOR"),
  ("gate", "GATE"),
  ("window", "WINDOW"),

  ("pipe", "PIPE"),
  ("plumbing", "PIPE"),
  ("duct", "DUCT"),
  ("hvac", "EQUIPMENT"),

  ("cable tray", "CABLE_TRAY"),
  ("tray", "CABLE_TRAY"),
  ("cable", "CABLE"),
  ("conduit", "CABLE"),

  ("valve", "VALVE"),
  ("pump", "PUMP"),
  ("tank", "TANK"),
  ("fan", "FAN"),
  ("chiller", "CHILLER"),
  ("boiler", "BOILER"),

  ("fixture", "FIXTURE"),
  ("light", "LIGHT_FIXTURE"),
  ("lamp", "LAMP"),
  ("outlet", "OUTLET"),

  ("kerb", "KERB"),
  ("curb", "KERB"),
  ("pavement", "PAVEMENT"),
  ("road", "PAVEMENT"),
  ("rail", "RAIL"),
  ("track", "TRACK"),
  ("sleeper", "TRACK_SLEEPER"),

  ("rebar", "REBAR"),
  ("reinforcement", "REBAR"),
  ("tendon", "TENDON"),
]

DISCIPLINE_BY_ROLE: dict[str, str] = {
  role: discipline
  for discipline, group in _ROLES_BY_DISCIPLINE.items()
  for role in group.values()
}
 
DISCIPLINE_BY_ROLE.update({
  "SLAB_FOUNDATION": "STRUCTURAL",
  "SLAB_ROOF": "STRUCTURAL",
  "SLAB_LANDING": "STRUCTURAL",
  "SLAB_PAVING": "SITE_CIVIL",
  "SIDEWALK": "SITE_CIVIL",
  "WALL_EXTERNAL": "ARCHITECTURAL",
  "WALL_INTERNAL": "ARCHITECTURAL",
  "WALL_RETAINING": "STRUCTURAL",
  "WALL_PARAPET": "ARCHITECTURAL",
  "WALL_SHEAR": "STRUCTURAL",
  "LINTEL": "STRUCTURAL",
  "GIRDER_SEGMENT": "STRUCTURAL",
  "EDGE_BEAM": "STRUCTURAL",
  "DIAPHRAGM": "STRUCTURAL",
  "CORNICE": "ARCHITECTURAL",
  "FLOOR_FINISH": "ARCHITECTURAL",
  "CEILING": "ARCHITECTURAL",
  "CLADDING": "ARCHITECTURAL",
  "ROOFING": "ARCHITECTURAL",
  "INSULATION": "ARCHITECTURAL",
  "MEMBRANE": "ARCHITECTURAL",
  "MOLDING": "ARCHITECTURAL",
  "SKIRTING": "ARCHITECTURAL",
  "GATE": "ARCHITECTURAL",
  "TRAPDOOR": "ARCHITECTURAL",
  "TURNSTILE": "ARCHITECTURAL",
  "BOOM_BARRIER": "ARCHITECTURAL",
  "TRACK_SLAB": "SITE_CIVIL",
  "WEARING_SLAB": "SITE_CIVIL",
  "TRACK_SLEEPER": "SITE_CIVIL",
  "TRACK_FROG": "SITE_CIVIL",
  "TRACK_DERAILER": "SITE_CIVIL",
  "TRACK_BLOCKING_DEVICE": "SITE_CIVIL",
  "TRACK_VEHICLE_STOP": "SITE_CIVIL",
})

DISCIPLINE_BY_ROLE.pop("UNKNOWN", None)
DEFAULT_DISCIPLINE = "UNKNOWN"
 
WALL_ROLES = frozenset({"WALL", "WALL_EXTERNAL", "WALL_INTERNAL", "WALL_RETAINING", "WALL_PARAPET", "WALL_SHEAR", "CURTAIN_WALL",})

SLAB_ROLES = frozenset({"SLAB", "SLAB_FOUNDATION", "SLAB_ROOF", "SLAB_LANDING", "SLAB_PAVING", "ROOF", "COVERING", "PLATE", "FLOOR_FINISH", "CEILING", "CLADDING", "ROOFING", "INSULATION",
  "MEMBRANE", "PAVEMENT", "COURSE", "SIDEWALK", "TRACK_SLAB", "WEARING_SLAB",})

LENGTH_ROLES = frozenset({"PIPE", "DUCT", "CABLE", "CABLE_TRAY", "MEP_SEGMENT", "CONVEYOR", "RAILING", "MEMBER", "KERB", "RAIL", "SKIRTING", "MOLDING", "TRACK_SLEEPER",})
LINEAR_ROLES = LENGTH_ROLES | {"BEAM", "LINTEL", "GIRDER_SEGMENT", "EDGE_BEAM", "DIAPHRAGM",}

AREA_ROLES = frozenset({"ROOF", "COVERING", "CURTAIN_WALL", "PLATE", "FLOOR_FINISH", "CEILING", "CLADDING", "ROOFING", "INSULATION", "MEMBRANE", "PAVEMENT", "SHADING_DEVICE",
  "SIDEWALK", "TRACK_SLAB", "WEARING_SLAB",
})

COUNT_ROLES = frozenset({"DOOR", "WINDOW", "FIXTURE", "FURNISHING", "TRANSPORT", "BEARING", "ACCESSORY", "FASTENER", "SIGN", "SIGNAL", "GATE", "TRAPDOOR", "TURNSTILE", "BOOM_BARRIER", "DISTRIBUTION_BOARD",
  "DISTRIBUTION_POINT", "ELECTRIC_STORAGE", "GENERATOR", "MOTOR", "ELECTRIC_CONTROL", "ELECTRIC_APPLIANCE", "JUNCTION_BOX", "LAMP", "LIGHT_FIXTURE", "OUTLET", "PROTECTIVE_DEVICE", "SWITCH_DEVICE", "TRANSFORMER",
   "SOLAR_DEVICE", "PIPE_FITTING", "VALVE", "PUMP", "TANK", "SANITARY_FIXTURE", "WASTE_TERMINAL", "STACK_TERMINAL", "INTERCEPTOR", "FLOW_METER", "CHAMBER", "MEDICAL_DEVICE",

    "DUCT_FITTING", "DUCT_SILENCER", "AIR_TERMINAL", "AIR_TERMINAL_BOX", "DAMPER", "FAN", "FILTER", "COIL", "CHILLER", "CONDENSER", "COOLED_BEAM", "COOLING_TOWER", "EVAPORATIVE_COOLER", "EVAPORATOR", "HEAT_EXCHANGER",
    "HUMIDIFIER", "BOILER", "BURNER", "COMPRESSOR", "UNITARY_EQUIPMENT", "SPACE_HEATER", "HEAT_RECOVERY", "ENGINE",

    "FIRE_TERMINAL", "ALARM", "AV_APPLIANCE", "COMMUNICATIONS_APPLIANCE", "SENSOR", "ACTUATOR", "CONTROLLER", "INSTRUMENT", "CONTROL_PANEL", "TRACK_FROG", "TRACK_DERAILER", 
      "TRACK_BLOCKING_DEVICE", "TRACK_VEHICLE_STOP", "MOORING_DEVICE", "NAVIGATION_ELEMENT",
    }) | (
     frozenset(role for role, disc in DISCIPLINE_BY_ROLE.items() if disc.startswith("MEP_")) - LENGTH_ROLES
    )

NO_LEGACY_BOQ_ROLES = frozenset({"REBAR", "REBAR_MESH", "TENDON", "ASSEMBLY", "FASTENER",})

MESH_FALLBACK_ROLES = (
  WALL_ROLES
  | SLAB_ROLES
  | LINEAR_ROLES
  | {
    "COLUMN",
    "FOOTING",
    "PILE",
    "CAISSON",
    "STAIR",
    "RAMP",
    "BUILDING_PART",
    "EARTHWORKS",
    "EARTHWORKS_CUT",
    "EARTHWORKS_FILL",
    "PAVEMENT",
    "COURSE",
    "KERB",
  }
)

MESH_FALLBACK_ROLES = frozenset(
  role for role in MESH_FALLBACK_ROLES
  if not DISCIPLINE_BY_ROLE.get(role, "").startswith("MEP_")
)
 
QUANTITY_PROPS_BY_KIND: dict[str, tuple[str, ...]] = {
  "volume": ("NetVolume", "GrossVolume"),
  "area": ("NetArea", "GrossArea", "NetSideArea", "GrossSideArea"),
  "length": ("Length",),
}

DEFAULT_QUANTITY_KIND_ORDER: tuple[str, ...] = ("volume", "area", "length")

QUANTITY_KIND_ORDER_BY_ROLE: dict[str, tuple[str, ...]] = {
  **{
    role: ("count",)
    for role in COUNT_ROLES
  },

  **{
    role: ("area", "volume")
    for role in AREA_ROLES
  },

  **{
    role: ("length", "volume")
    for role in LENGTH_ROLES
  },
  
  "COURSE": ("volume", "area"),

  "REBAR": ("length",),
  "TENDON": ("length",),
  "REBAR_MESH": ("area",),

  "EARTHWORKS": ("volume",),
  "EARTHWORKS_CUT": ("volume",),
  "EARTHWORKS_FILL": ("volume",),

  "FOOTING": ("volume", "area"),
  "CAISSON": ("volume", "length"),
  "PILE": ("length", "volume"),
  "COLUMN": ("volume", "length"),
  "BEAM": ("volume", "length"),
  "LINTEL": ("volume", "length"),
  "MEMBER": ("length", "volume"),
  "SLAB": ("volume", "area"),
  "SLAB_FOUNDATION": ("volume", "area"),
  "SLAB_ROOF": ("volume", "area"),
  "WALL": ("volume", "area"),
  "WALL_EXTERNAL": ("volume", "area"),
  "WALL_INTERNAL": ("volume", "area"),
  "WALL_RETAINING": ("volume", "area"),
  "WALL_PARAPET": ("volume", "area"),
  "WALL_SHEAR": ("volume", "area"),

  "LANDSCAPE": ("area", "volume", "count"),
  "TRACK": ("length", "count"),
}

 
REQUIRED_DIMENSIONS_BY_ROLE: dict[str, tuple[str, ...]] = {
  **{
    role: ("length", "height", "thickness")
    for role in WALL_ROLES
    if role != "CURTAIN_WALL"
  },
  "SLAB": ("thickness",),
  "SLAB_FOUNDATION": ("thickness",),
  "SLAB_ROOF": ("thickness",),
  "SLAB_LANDING": ("thickness",),
  "BEAM": ("length",),
  "LINTEL": ("length",),
  "GIRDER_SEGMENT": ("length",),
  "EDGE_BEAM": ("length",),
  "COLUMN": ("height",),
  "PIPE": ("length",),
  "DUCT": ("length",),
  "CABLE": ("length",),
  "CABLE_TRAY": ("length",),
  "RAILING": ("length",),
  "KERB": ("length",),
  "RAIL": ("length",),

  "PAVEMENT": ("thickness",),
  "COURSE": ("thickness",),
}
 
GEOMETRY_KINDS = ("EXTRUDED_PROFILE", "AXIS_SWEPT", "BOX_ONLY", "QTO_ONLY", "UNSUPPORTED")
NORMALIZATION_STATUSES = ("PENDING", "VALID", "WARNING", "INVALID")
 
LOW_CLASSIFICATION_CONFIDENCE = 0.6
DEFAULT_MESH_FALLBACK_LIMIT = 3000

QUANTITY_LOOKUP_ORDER: list[tuple[list[str], str]] = [
  (["NetVolume", "GrossVolume"], "m3"),
  (["NetArea", "GrossArea"], "m2"),
  (["Length"], "m"),
]