import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useCreateSpace, useUpdateSpace } from "../hooks/useSpacesSchedules";
import { EXTERNAL_CATEGORIES, mm2ToM2, mmToM, SPACE_CATEGORIES, toInput } from "../utils/drawings-boq.utils";
import type { LevelOption, SpaceResponse, SpaceUpdateRequest } from "../types/drawings-boq.types";
import { useTranslation } from "react-i18next";

interface SpaceFormDialogProps {
  projectId: string;
  space?: SpaceResponse;
  levels: LevelOption[];
  onClose: () => void;
}

const selectCls = "w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[12.5px] text-[var(--color-text-primary)]";

export function SpaceFormDialog({ projectId, space, levels, onClose }: SpaceFormDialogProps) {
  const { t } = useTranslation();
  const create = useCreateSpace(projectId);
  const update = useUpdateSpace(projectId);
  const { showToast } = useToast();

  const initial = {
    number: space?.number ?? "", name: space?.name ?? "", long_name: space?.long_name ?? "", usage_text: space?.usage_text ?? "",
    category: space?.category ?? "UNKNOWN", level_id: space?.level_id ?? "", is_external: space?.is_external ?? false,
    area: toInput(mm2ToM2(space?.net_floor_area_mm2)), perimeter: toInput(mmToM(space?.perimeter_mm)), height: toInput(mmToM(space?.height_mm)),
  };
  
  const [f, setF] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof typeof initial>(key: K, value: (typeof initial)[K]) => setF((cur) => ({ ...cur, [key]: value }));

  const num = (v: string) => (v === "" ? null : Number(v));
  const badNumber = [f.area, f.perimeter, f.height].some((v) => v !== "" && !(Number(v) > 0));
  const hasName = f.number.trim() !== "" || f.name.trim() !== "";
  const pending = create.isPending || update.isPending;

  function changed(): SpaceUpdateRequest {
    const p: SpaceUpdateRequest = {};
    if (f.number !== initial.number) p.number = f.number;
    if (f.name !== initial.name) p.name = f.name;
    if (f.long_name !== initial.long_name) p.long_name = f.long_name;
    if (f.usage_text !== initial.usage_text) p.usage_text = f.usage_text;
    if (f.category !== initial.category && f.category) p.category = f.category;
    if (f.level_id !== initial.level_id) p.level_id = f.level_id || null;
    if (f.is_external !== initial.is_external) p.is_external = f.is_external;
    if (f.area !== initial.area) p.floor_area_m2 = num(f.area);
    if (f.perimeter !== initial.perimeter) p.perimeter_m = num(f.perimeter);
    if (f.height !== initial.height) p.height_m = num(f.height);
    return p;
  }
  const dirty = space ? Object.keys(changed()).length > 0 : true;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const done = (title: string) => ({
      onSuccess: () => { onClose(); showToast({ tone: "success", title }); },
      onError: (e: unknown) => setError(getApiErrorMessage(e, t("spaces.form.error", "Couldn't save this space."))),
    });
    if (space) {
      update.mutate({ spaceId: space.id, payload: changed() }, done(t("spaces.form.updated", "Space updated")));
    } else {
      create.mutate(
        {
          number: f.number.trim() || null, name: f.name.trim() || null, long_name: f.long_name.trim() || null,
          usage_text: f.usage_text.trim() || null, category: f.category || "UNKNOWN", level_id: f.level_id || null,
          is_external: f.is_external, floor_area_m2: num(f.area), perimeter_m: num(f.perimeter), height_m: num(f.height),
        },
        done(t("spaces.form.created", "Space created")),
      );
    }
  }

  return (
    <Modal
      title={space ? t("spaces.form.editTitle", "Edit space") : t("spaces.form.createTitle", "Add space")}
      description={space?.source === "IFC" ? t("spaces.form.ifcHint", "Changed area, perimeter or height values are recorded as manual overrides on this model space.") : t("spaces.form.manualHint", "A manual space needs a number or a name. Add its floor area so finishes can be measured.")}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("spaces.form.number", "Room number")}><input className={inputClass} value={f.number} maxLength={100} onChange={(e) => set("number", e.target.value)} /></Field>
          <Field label={t("spaces.form.name", "Name")}><input className={inputClass} value={f.name} maxLength={300} onChange={(e) => set("name", e.target.value)} /></Field>
          <Field label={t("spaces.form.longName", "Long name")}><input className={inputClass} value={f.long_name} maxLength={500} onChange={(e) => set("long_name", e.target.value)} /></Field>
          <Field label={t("spaces.form.usage", "Usage")}><input className={inputClass} value={f.usage_text} maxLength={300} onChange={(e) => set("usage_text", e.target.value)} /></Field>
          <Field label={t("spaces.form.category", "Category")}>
            <select className={selectCls} value={f.category} onChange={(e) => { set("category", e.target.value); if (!space) set("is_external", EXTERNAL_CATEGORIES.has(e.target.value)); }}>
              {!(SPACE_CATEGORIES as readonly string[]).includes(f.category) ? <option value={f.category}>{f.category}</option> : null}
              {SPACE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label={t("spaces.form.level", "Level")}>
            <select className={selectCls} value={f.level_id} onChange={(e) => set("level_id", e.target.value)}>
              <option value="">{t("spaces.form.noLevel", "No level")}</option>
              {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </Field>
          <Field label={t("spaces.form.area", "Floor area (m²)")}><input className={inputClass} type="number" step="any" min="0" value={f.area} onChange={(e) => set("area", e.target.value)} /></Field>
          <Field label={t("spaces.form.perimeter", "Perimeter (m)")}><input className={inputClass} type="number" step="any" min="0" value={f.perimeter} onChange={(e) => set("perimeter", e.target.value)} /></Field>
          <Field label={t("spaces.form.height", "Height (m)")}><input className={inputClass} type="number" step="any" min="0" value={f.height} onChange={(e) => set("height", e.target.value)} /></Field>
          <label className="flex items-end gap-2 pb-2 text-[12.5px] text-[var(--color-text-secondary)]">
            <input type="checkbox" checked={f.is_external} onChange={(e) => set("is_external", e.target.checked)} />
            {t("spaces.form.external", "External space (balcony, terrace…)")}
          </label>
        </div>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button type="submit" variant="primary" disabled={pending || !hasName || badNumber || !dirty}>{pending ? t("common.saving", "Saving…") : t("common.save", "Save")}</Button>
        </div>
      </form>
    </Modal>
  );
}
