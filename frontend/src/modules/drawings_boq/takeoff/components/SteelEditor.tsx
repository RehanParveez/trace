import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, inputClass } from "../../../organizations/components/OrganizationUi";
import type { TakeoffCandidate } from "../types/takeoff.types";
import { BAR_ROLES, effectiveSteel, emptyForm, formFromSteel, isMoreCategory, readSteel, steelFamily, steelFromForm, steelLine } from "../utils/steel";
import type { SteelForm, SteelFormError, SteelSet } from "../utils/steel";

interface Props {
  c: TakeoffCandidate;
  typed: SteelSet | undefined;
  canEdit: boolean;
  onChange: (id: string, steel: SteelSet | null) => void;
}

const ERROR_TEXT: Record<SteelFormError, string> = {
  BARS_INCOMPLETE: "Give both the number of bars and the bar number.",
  BAR_OUT_OF_RANGE: "A bar number is 2 to 12 (#4 is half an inch).",
  COUNT_OUT_OF_RANGE: "Give 1 to 30 bars.",
  SPACING_OUT_OF_RANGE: "Spacing is 2 to 24 inches.",
  RING_INCOMPLETE: "Give both the ring bar number and its spacing.",
  MESH_INCOMPLETE: "Give both the mesh bar number and its spacing.",
  ACROSS_INCOMPLETE: "Give both the bar number and the spacing of the second way, or leave both empty.",
  SLAB_MESH_INCOMPLETE: "Give both the bar number and the spacing of the slab mesh, or leave both empty.",
  NOTHING_TYPED: "Type the bars, or clear the typed steel.",
};

export function SteelEditor({ c, typed, canEdit, onChange }: Props) {
  const { t } = useTranslation();
  const family = steelFamily(c.category);
  const read = readSteel(c.params as Record<string, unknown>);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<SteelForm>(() => formFromSteel(typed ?? read));
  const [errors, setErrors] = useState<SteelFormError[]>([]);
  if (family === null) return null;
  const { steel, source } = effectiveSteel(read, typed);
  const disagree = c.notes.some((n) => n.code === "STEEL_DETAILS_DISAGREE");

  const apply = () => {
    const r = steelFromForm(form, c.category);
    setErrors(r.errors);
    if (r.steel) {
      onChange(c.id, r.steel);
      setOpen(false);
    }
  };
  const clear = () => {
    setForm(formFromSteel(read));
    setErrors([]);
    onChange(c.id, null);
    setOpen(false);
  };
  const setBar = (role: string, field: "n" | "bar", value: string) => setForm({ ...form, bars: { ...form.bars, [role]: { n: form.bars[role]?.n ?? "", bar: form.bars[role]?.bar ?? "", [field]: value } } });

  return (
    <div className="mt-1.5 rounded-[8px] bg-[var(--color-surface-muted)] p-2" data-testid="steel-editor" data-source={source}>
      <div className="flex flex-wrap items-center gap-2 text-[11.5px]">
        <span className="font-semibold">{t("boq.takeoff.steel.title", "Steel")}</span>
        {source === "PRINTED" ? <Badge tone="green">{t("boq.takeoff.steel.printed", "printed on drawing")}</Badge> : null}
        {source === "TYPED" ? <Badge tone="gold">{t("boq.takeoff.steel.typed", "typed by you")}</Badge> : null}
        {source === "NONE" ? <Badge tone="red">{t("boq.takeoff.steel.missing", "not read")}</Badge> : null}
        <span className="text-[var(--color-text-secondary)]" data-testid="steel-line">{steelLine(steel)}</span>
        {canEdit ? (
          <Button size="sm" variant="ghost" className="ml-auto" onClick={() => setOpen(!open)} data-testid="steel-toggle">
            {open ? t("boq.takeoff.steel.close", "Close") : source === "NONE" ? t("boq.takeoff.steel.add", "Type the bars") : t("boq.takeoff.steel.edit", "Change")}
          </Button>
        ) : null}
      </div>
      {source === "NONE" ? (
        <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">
          {disagree
            ? t("boq.takeoff.steel.disagree", "Two details print different bars for this mark. Type the ones you want.")
            : t("boq.takeoff.steel.none", "No bars were found for this member. If you leave it empty, no steel is taken for it.")}
        </div>
      ) : null}
      {open ? (
        <div className="mt-2 space-y-2" data-testid="steel-form">
          {family === "FRAME" ? (
            <>
              {(BAR_ROLES[c.category] ?? []).map((role) => (
                <div key={role} className="flex items-center gap-2 text-[12px]">
                  <span className="w-16">{t(`boq.derived.steelRole.${role}`, role)}</span>
                  <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="nos" value={form.bars[role]?.n ?? ""} onChange={(e) => setBar(role, "n", e.target.value)} aria-label={`${role} number`} data-testid={`steel-${role}-n`} />
                  <span>×  #</span>
                  <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="bar" value={form.bars[role]?.bar ?? ""} onChange={(e) => setBar(role, "bar", e.target.value)} aria-label={`${role} bar`} data-testid={`steel-${role}-bar`} />
                </div>
              ))}
              <div className="flex items-center gap-2 text-[12px]">
                <span className="w-16">{t("boq.derived.steelRole.ring", "ring")}</span>
                <span>#</span>
                <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="bar" value={form.ringBar} onChange={(e) => setForm({ ...form, ringBar: e.target.value })} aria-label="ring bar" data-testid="steel-ring-bar" />
                <span>@</span>
                <input className={`${inputClass} !h-7 !w-16 !px-2`} inputMode="decimal" placeholder="in" value={form.ringSpacingIn} onChange={(e) => setForm({ ...form, ringSpacingIn: e.target.value })} aria-label="ring spacing in inches" data-testid="steel-ring-spacing" />
                <span>in c/c</span>
              </div>
            </>
          ) : (
            <div className="flex flex-wrap items-center gap-2 text-[12px]">
              <span className="w-16">{t("boq.takeoff.steel.mesh", "mesh")}</span>
              <span>#</span>
              <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="bar" value={form.meshBar} onChange={(e) => setForm({ ...form, meshBar: e.target.value })} aria-label="mesh bar" data-testid="steel-mesh-bar" />
              <span>@</span>
              <input className={`${inputClass} !h-7 !w-16 !px-2`} inputMode="decimal" placeholder="in" value={form.meshSpacingIn} onChange={(e) => setForm({ ...form, meshSpacingIn: e.target.value })} aria-label="mesh spacing in inches" data-testid="steel-mesh-spacing" />
              <span>in c/c</span>
              <select className={`${inputClass} !h-7 !w-auto !px-2`} value={form.ways} onChange={(e) => setForm({ ...form, ways: e.target.value as "1" | "2" })} aria-label="ways">
                <option value="2">{t("boq.takeoff.steel.bothWays", "both ways")}</option>
                <option value="1">{t("boq.takeoff.steel.oneWay", "one way")}</option>
              </select>
              <select className={`${inputClass} !h-7 !w-auto !px-2`} value={form.layers} onChange={(e) => setForm({ ...form, layers: e.target.value as "1" | "2" })} aria-label="layers">
                <option value="1">{t("boq.takeoff.steel.oneLayer", "one layer")}</option>
                <option value="2">{t("boq.takeoff.steel.twoLayers", "top and bottom")}</option>
              </select>
            </div>
          )}
          {family === "MESH" && isMoreCategory(c.category) ? (
            <div className="flex flex-wrap items-center gap-2 text-[12px]" data-testid="steel-across">
              <span className="w-16">{t("boq.takeoff.steel.across", "second way")}</span>
              <span>#</span>
              <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="bar" value={form.acrossBar} onChange={(e) => setForm({ ...form, acrossBar: e.target.value })} aria-label="second way bar" data-testid="steel-across-bar" />
              <span>@</span>
              <input className={`${inputClass} !h-7 !w-16 !px-2`} inputMode="decimal" placeholder="in" value={form.acrossSpacingIn} onChange={(e) => setForm({ ...form, acrossSpacingIn: e.target.value })} aria-label="second way spacing in inches" data-testid="steel-across-spacing" />
              <span>in c/c</span>
              <span className="text-[11px] text-[var(--color-text-muted)]">{t("boq.takeoff.steel.acrossHint", "Only when the two ways differ.")}</span>
            </div>
          ) : null}
          {(c.category as string) === "TANK" ? (
            <div className="flex flex-wrap items-center gap-2 text-[12px]" data-testid="steel-slab-mesh">
              <span className="w-16">{t("boq.takeoff.steel.slabMesh", "top and bottom slab")}</span>
              <span>#</span>
              <input className={`${inputClass} !h-7 !w-14 !px-2`} inputMode="numeric" placeholder="bar" value={form.slabBar} onChange={(e) => setForm({ ...form, slabBar: e.target.value })} aria-label="slab mesh bar" data-testid="steel-slab-bar" />
              <span>@</span>
              <input className={`${inputClass} !h-7 !w-16 !px-2`} inputMode="decimal" placeholder="in" value={form.slabSpacingIn} onChange={(e) => setForm({ ...form, slabSpacingIn: e.target.value })} aria-label="slab mesh spacing in inches" data-testid="steel-slab-spacing" />
              <span>in c/c</span>
              <select className={`${inputClass} !h-7 !w-auto !px-2`} value={form.slabWays} onChange={(e) => setForm({ ...form, slabWays: e.target.value as "1" | "2" })} aria-label="slab ways">
                <option value="2">{t("boq.takeoff.steel.bothWays", "both ways")}</option>
                <option value="1">{t("boq.takeoff.steel.oneWay", "one way")}</option>
              </select>
              <select className={`${inputClass} !h-7 !w-auto !px-2`} value={form.slabLayers} onChange={(e) => setForm({ ...form, slabLayers: e.target.value as "1" | "2" })} aria-label="slab layers">
                <option value="1">{t("boq.takeoff.steel.oneLayer", "one layer")}</option>
                <option value="2">{t("boq.takeoff.steel.twoLayers", "top and bottom")}</option>
              </select>
            </div>
          ) : null}
          {errors.map((e) => <div key={e} className="text-[11.5px] text-[var(--color-danger)]" data-testid="steel-error">{t(`boq.takeoff.steel.error.${e}`, ERROR_TEXT[e])}</div>)}
          <div className="flex gap-2">
            <Button size="sm" variant="primary" onClick={apply} data-testid="steel-apply">{t("boq.takeoff.steel.use", "Use these bars")}</Button>
            {typed ? <Button size="sm" variant="ghost" onClick={clear} data-testid="steel-clear">{t("boq.takeoff.steel.clear", "Back to the drawing")}</Button> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export { emptyForm };
