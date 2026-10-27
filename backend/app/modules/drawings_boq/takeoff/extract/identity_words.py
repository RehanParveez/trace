from __future__ import annotations

DISCIPLINE_WORDS = (
  ("ELECTRICAL", r"\bELECTRIC\w*", 3),
  ("ELECTRICAL", r"\bCEILING\s+LIGHT\w*|\bLIGHT(?:S|ING)\b|\bSOCKETS?\b|\bWIRING\b|\bCCTV\b|\bLCD\b|\bCAM(?:E)?RAS?\b|\bTELEPHONE\b|\bSWITCH(?:ES|BOARD)?\b|\bCEILING\s+FANS?\b|\bEXH?AUST\b", 2),
  ("PLUMBING", r"\bPLUMBING\b|\bPUBLIC\s+HEALTH\b", 3),
  ("PLUMBING", r"\bSEWERAGE\b|\bSEWER\b|\bWATER\s+SUPPLY\b|\bDRA?I?NAGE\b|\bSANITARY\b|\bSEPTIC\b|\bMANHOLES?\b", 2),
  ("HVAC", r"\bHVAC\b|\bAIR\s*CONDITION\w*", 3),
  ("HVAC", r"\bA\.?\s?C\.?\s+POINTS?\b|\bAC\s+POINTS?\b|\bDUCT(?:S|ING)?\b|\bVENTILATION\b|\bSPLIT\s+UNITS?\b", 2),
  ("FIRE", r"\bFIRE\s+(?:FIGHTING|ALARM|PROTECTION|SAFETY)\b", 3),
  ("FIRE", r"\bSPRINKLERS?\b|\bHYDRANTS?\b", 2),
  ("GAS", r"\bSUI\s+GAS\b|\bGAS\s+(?:PIPE|LINE|LAYOUT|PLAN)\b", 3),
  ("GAS", r"\bGAS\b", 1.5),
  ("STRUCTURAL", r"\bSTR\w?CT\w?R(?:E|AL)\b", 3),
  ("STRUCTURAL", r"\bFOUNDATIONS?\b|\bFOOTINGS?\b|\bFRAMING\b|\bREINFORCEMENT\b|\bRAFT\b|\bPILES?\b|\bLINTELS?\b|\bX-?SECTIONS?\b", 2),
  ("STRUCTURAL", r"\bBEAMS?\b|\bCOLUMNS?\b|\bSLABS?\b", 1.5),
  ("ARCHITECTURAL", r"\bARCHITECT\w*", 3),
  ("ARCHITECTURAL", r"\bFURNITURE\b|\bELEVATIONS?\b|\bFINISH(?:ES|ING)?\b", 2),
  ("ARCHITECTURAL", r"\bMUMTY\b", 1),
  ("ARCHITECTURAL", r"\bFLOOR\s+PLAN\b|\bLAYOUT\b", 1),
  ("SITE", r"\bSITE\s+PLAN\b|\bLOCATION\s+PLAN\b|\bPLOT\s+PLAN\b|\bKEY\s+PLAN\b", 3),
)

SERVICES = ("ELECTRICAL", "PLUMBING", "HVAC", "FIRE", "GAS")

SHEET_TYPE_WORDS = (
  ("LEGEND", r"\bLEGENDS?\b|\bSYMBOLS?\b|\bABBREVIATIONS?\b|\bDRAWING\s+LIST\b|\bINDEX\b"),
  ("SCHEDULE", r"\bSCHEDULES?\b"),
  ("SPEC", r"\bSPECIFICATIONS?\b|\bGENERAL\s+NOTES\b|\bBILL\s+OF\s+QUANTIT\w+"),
  ("SECTION", r"\bSECTIONS?\b|\bX-?SECTIONS?\b"),
  ("ELEVATION", r"\bELEVATIONS?\b"),
  ("DETAIL", r"\bDETAILS?\b"),
  ("POINTS_PLAN", r"\bPOINTS?\b"),
  ("PLAN", r"\bPLANS?\b|\bLAYOUTS?\b|\bFRAMING\b|\bMUMTY\b|\bFLOOR\b|\bROOF\b|\bFOUNDATIONS?\b|\bBEAM\b|\bSLAB\b"),
  ("PLAN", r"\bDRAWING\s+[A-Z]{1,2}-?\d{1,3}\b"),
)
PLAN_TYPES = ("PLAN", "POINTS_PLAN")

NOISE_LINE = r"^[^A-Za-z]*(?:[A-Za-z]{0,2})?[^A-Za-z]*$"
