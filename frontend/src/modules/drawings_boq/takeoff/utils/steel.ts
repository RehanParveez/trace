export const MM_PER_INCH = 25.4;

export interface BarSet {
  n: number;
  bar?: number;
  dia_mm?: number;
}

export interface RingSet {
  bar?: number;
  dia_mm?: number;
  spacing_mm: number;
  dense_spacing_mm?: number;
  dense_zone_mm?: number;
}

export interface MeshSet {
  bar?: number;
  dia_mm?: number;
  spacing_mm: number;
  ways: 1 | 2;
  layers: 1 | 2;
  across?: { bar?: number; dia_mm?: number; spacing_mm: number };
}

export interface SteelSet {
  bottom?: BarSet;
  top?: BarSet;
  bars?: BarSet;
  vertical?: BarSet;
  extra?: BarSet;
  ring?: RingSet;
  mesh?: MeshSet;
  slab_mesh?: MeshSet;
}

export type SteelFamily = "FRAME" | "MESH";

export const MORE_CATEGORIES = ["STAIR", "TANK", "PARAPET", "CHAJJA", "BALCONY_SLAB"] as const;

export function isMoreCategory(category: string): boolean {
  return (MORE_CATEGORIES as readonly string[]).includes(category);
}

export function steelFamily(category: string): SteelFamily | null {
  if (category === "COLUMN" || category === "BEAM") return "FRAME";
  if (category === "FOOTING" || category === "SLAB" || isMoreCategory(category)) return "MESH";
  return null;
}

export const BAR_ROLES: Record<string, readonly string[]> = { COLUMN: ["vertical"], BEAM: ["bottom", "top"] };

function sizeText(g: { bar?: number; dia_mm?: number }): string {
  return g.bar ? `#${g.bar}` : `${g.dia_mm} mm`;
}

const inchText = (mm: number) => String(Math.round((mm / MM_PER_INCH) * 100) / 100);

export function steelLine(steel: SteelSet | null | undefined): string {
  if (!steel) return "";
  const parts: string[] = [];
  for (const role of ["bottom", "top", "bars", "vertical", "extra"] as const) {
    const g = steel[role];
    if (g) parts.push(`${g.n} ${sizeText(g)} ${role}`);
  }
  if (steel.ring) {
    const dense = steel.ring.dense_spacing_mm ? `, ${inchText(steel.ring.dense_spacing_mm)} in at the ends` : "";
    parts.push(`rings ${sizeText(steel.ring)} at ${inchText(steel.ring.spacing_mm)} in${dense}`);
  }
  if (steel.mesh) {
    parts.push(`mesh ${sizeText(steel.mesh)} at ${inchText(steel.mesh.spacing_mm)} in ${steel.mesh.ways === 1 ? "one way" : "both ways"}${steel.mesh.layers === 2 ? ", 2 layers" : ""}`);
    if (steel.mesh.across) {
      parts.push(`across ${sizeText(steel.mesh.across)} at ${inchText(steel.mesh.across.spacing_mm)} in`);
    }
  }
  if (steel.slab_mesh) {
    parts.push(`slab mesh ${sizeText(steel.slab_mesh)} at ${inchText(steel.slab_mesh.spacing_mm)} in ${steel.slab_mesh.ways === 1 ? "one way" : "both ways"}${steel.slab_mesh.layers === 2 ? ", 2 layers" : ""}`);
  }
  return parts.join(", ");
}

export interface SteelForm {
  bars: Record<string, { n: string; bar: string }>;
  ringBar: string;
  ringSpacingIn: string;
  meshBar: string;
  meshSpacingIn: string;
  ways: "1" | "2";
  layers: "1" | "2";
  acrossBar: string;
  acrossSpacingIn: string;
  slabBar: string;
  slabSpacingIn: string;
  slabWays: "1" | "2";
  slabLayers: "1" | "2";
}

const EMPTY_BAR = { n: "", bar: "" };

export function emptyForm(): SteelForm {
  return { bars: {}, ringBar: "", ringSpacingIn: "", meshBar: "", meshSpacingIn: "", ways: "2", layers: "1", acrossBar: "", acrossSpacingIn: "", slabBar: "", slabSpacingIn: "", slabWays: "2", slabLayers: "1" };
}

export function formFromSteel(steel: SteelSet | null | undefined): SteelForm {
  const form = emptyForm();
  if (!steel) return form;
  for (const role of ["bottom", "top", "bars", "vertical"] as const) {
    const g = steel[role];
    if (g?.bar) form.bars[role] = { n: String(g.n), bar: String(g.bar) };
  }
  if (steel.ring?.bar) {
    form.ringBar = String(steel.ring.bar);
    form.ringSpacingIn = inchText(steel.ring.spacing_mm);
  }
  if (steel.mesh?.bar) {
    form.meshBar = String(steel.mesh.bar);
    form.meshSpacingIn = inchText(steel.mesh.spacing_mm);
    form.ways = steel.mesh.ways === 1 ? "1" : "2";
    form.layers = steel.mesh.layers === 2 ? "2" : "1";
    if (steel.mesh.across?.bar) {
      form.acrossBar = String(steel.mesh.across.bar);
      form.acrossSpacingIn = inchText(steel.mesh.across.spacing_mm);
    }
  }
  if (steel.slab_mesh?.bar) {
    form.slabBar = String(steel.slab_mesh.bar);
    form.slabSpacingIn = inchText(steel.slab_mesh.spacing_mm);
    form.slabWays = steel.slab_mesh.ways === 1 ? "1" : "2";
    form.slabLayers = steel.slab_mesh.layers === 2 ? "2" : "1";
  }
  return form;
}

function whole(raw: string, low: number, high: number): number | null {
  const text = raw.trim();
  if (text === "" || !/^\d+$/.test(text)) return null;
  const n = Number(text);
  return n >= low && n <= high ? n : null;
}

function inches(raw: string): number | null {
  const text = raw.trim();
  if (text === "") return null;
  const n = Number(text);
  if (!Number.isFinite(n) || n < 2 || n > 24) return null;
  return Math.round(n * MM_PER_INCH * 10) / 10;
}

export type SteelFormError = "BARS_INCOMPLETE" | "BAR_OUT_OF_RANGE" | "COUNT_OUT_OF_RANGE" | "SPACING_OUT_OF_RANGE" | "RING_INCOMPLETE" | "MESH_INCOMPLETE" | "ACROSS_INCOMPLETE" | "SLAB_MESH_INCOMPLETE" | "NOTHING_TYPED";

function acrossFromForm(form: SteelForm, errors: SteelFormError[]): { bar: number; spacing_mm: number } | null {
  if (form.acrossBar.trim() === "" && form.acrossSpacingIn.trim() === "") return null;
  const bar = whole(form.acrossBar, 2, 12);
  const spacing = inches(form.acrossSpacingIn);
  if (form.acrossBar.trim() === "" || form.acrossSpacingIn.trim() === "") errors.push("ACROSS_INCOMPLETE");
  else if (bar === null) errors.push("BAR_OUT_OF_RANGE");
  else if (spacing === null) errors.push("SPACING_OUT_OF_RANGE");
  else return { bar, spacing_mm: spacing };
  return null;
}

function slabMeshFromForm(form: SteelForm, errors: SteelFormError[]): MeshSet | null {
  if (form.slabBar.trim() === "" && form.slabSpacingIn.trim() === "") return null;
  const bar = whole(form.slabBar, 2, 12);
  const spacing = inches(form.slabSpacingIn);
  if (form.slabBar.trim() === "" || form.slabSpacingIn.trim() === "") errors.push("SLAB_MESH_INCOMPLETE");
  else if (bar === null) errors.push("BAR_OUT_OF_RANGE");
  else if (spacing === null) errors.push("SPACING_OUT_OF_RANGE");
  else return { bar, spacing_mm: spacing, ways: form.slabWays === "1" ? 1 : 2, layers: form.slabLayers === "2" ? 2 : 1 };
  return null;
}

export interface SteelFormResult {
  steel: SteelSet | null;
  errors: SteelFormError[];
}

export function steelFromForm(form: SteelForm, category: string): SteelFormResult {
  const family = steelFamily(category);
  const errors: SteelFormError[] = [];
  const steel: SteelSet = {};
  if (family === "FRAME") {
    for (const role of BAR_ROLES[category] ?? []) {
      const row = form.bars[role] ?? EMPTY_BAR;
      if (row.n.trim() === "" && row.bar.trim() === "") continue;
      const n = whole(row.n, 1, 30);
      const bar = whole(row.bar, 2, 12);
      if (row.n.trim() === "" || row.bar.trim() === "") errors.push("BARS_INCOMPLETE");
      else if (n === null) errors.push("COUNT_OUT_OF_RANGE");
      else if (bar === null) errors.push("BAR_OUT_OF_RANGE");
      else steel[role as "bottom" | "top" | "vertical"] = { n, bar };
    }
    if (form.ringBar.trim() !== "" || form.ringSpacingIn.trim() !== "") {
      const bar = whole(form.ringBar, 2, 12);
      const spacing = inches(form.ringSpacingIn);
      if (form.ringBar.trim() === "" || form.ringSpacingIn.trim() === "") errors.push("RING_INCOMPLETE");
      else if (bar === null) errors.push("BAR_OUT_OF_RANGE");
      else if (spacing === null) errors.push("SPACING_OUT_OF_RANGE");
      else steel.ring = { bar, spacing_mm: spacing };
    }
  } else if (family === "MESH") {
    if (form.meshBar.trim() !== "" || form.meshSpacingIn.trim() !== "") {
      const bar = whole(form.meshBar, 2, 12);
      const spacing = inches(form.meshSpacingIn);
      if (form.meshBar.trim() === "" || form.meshSpacingIn.trim() === "") errors.push("MESH_INCOMPLETE");
      else if (bar === null) errors.push("BAR_OUT_OF_RANGE");
      else if (spacing === null) errors.push("SPACING_OUT_OF_RANGE");
      else {
        steel.mesh = { bar, spacing_mm: spacing, ways: form.ways === "1" ? 1 : 2, layers: form.layers === "2" ? 2 : 1 };
        const across = isMoreCategory(category) ? acrossFromForm(form, errors) : null;
        if (across) steel.mesh.across = across;
      }
    }
  }
  if (category === "TANK") {
    const slab = slabMeshFromForm(form, errors);
    if (slab) steel.slab_mesh = slab;
  }
  if (errors.length === 0 && Object.keys(steel).length === 0) errors.push("NOTHING_TYPED");
  return { steel: errors.length === 0 ? steel : null, errors };
}

export function effectiveSteel(read: SteelSet | null | undefined, typed: SteelSet | null | undefined): { steel: SteelSet | null; source: "TYPED" | "PRINTED" | "NONE" } {
  if (typed && Object.keys(typed).length > 0) return { steel: typed, source: "TYPED" };
  if (read && Object.keys(read).length > 0) return { steel: read, source: "PRINTED" };
  return { steel: null, source: "NONE" };
}

export function steelForAccept(ids: readonly string[], typed: Record<string, SteelSet>): Record<string, SteelSet> | undefined {
  const out: Record<string, SteelSet> = {};
  for (const id of ids) {
    const s = typed[id];
    if (s && Object.keys(s).length > 0) out[id] = s;
  }
  return Object.keys(out).length > 0 ? out : undefined;
}

export function readSteel(params: Record<string, unknown> | null | undefined): SteelSet | null {
  const raw = params?.steel;
  return raw && typeof raw === "object" ? (raw as SteelSet) : null;
}
