export const ROOM_TYPES = ["BEDROOM", "BATH", "PWD", "WC", "KITCHEN", "LOUNGE", "DINING", "DRAWING", "PORCH", "TERRACE", "PASSAGE", "LAWN", "LOOK_BELOW", "VOID", "DOUBLE_HEIGHT", "STAIR", "STORE", "SERVANT", "OTHER"] as const;
export type RoomType = (typeof ROOM_TYPES)[number];

const TEXT: Record<string, string> = {
  BEDROOM: "Bedroom", BATH: "Bath", PWD: "Powder room", WC: "W.C", KITCHEN: "Kitchen", LOUNGE: "Lounge", DINING: "Dining", DRAWING: "Drawing room", PORCH: "Porch", TERRACE: "Terrace",
  PASSAGE: "Passage", LAWN: "Lawn", LOOK_BELOW: "Look below", VOID: "Void", DOUBLE_HEIGHT: "Double height", STAIR: "Stair", STORE: "Store", SERVANT: "Servant's room", OTHER: "Other",
};

export function roomTypeText(type: string): string {
  return TEXT[type] ?? type;
}

export interface FinishRule {
  key: string;
  scope: Record<string, string>;
  value: unknown;
}

export interface FinishRules {
  rules: FinishRule[];
}

export interface FinishRulesUpdate {
  rules: FinishRule[];
  note?: string | null;
}
