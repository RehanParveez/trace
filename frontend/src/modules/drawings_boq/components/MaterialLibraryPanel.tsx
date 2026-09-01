import { useState } from "react";
import type { FormEvent } from "react";
import { Button, EmptyState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import { useCreateMaterialLibraryEntry, useMaterialLibrary, useUpdateMaterialLibraryEntry } from "../hooks";
import { formatCurrency } from "../utils/drawings-boq.utils";
import type { MaterialLibraryEntry } from "../types/drawings-boq.types";

interface MaterialLibraryPanelProps {
  canManage: boolean;
}

interface MaterialLibraryRowProps {
  entry: MaterialLibraryEntry;
  canManage: boolean;
  onSaveRate: (rate: number | null) => void;
}

export function MaterialLibraryPanel({ canManage }: MaterialLibraryPanelProps) {
  const libraryQuery = useMaterialLibrary();
  const createEntry = useCreateMaterialLibraryEntry();

  const [formOpen, setFormOpen] = useState(false);
  const [rawText, setRawText] = useState("");
  const [normalizedName, setNormalizedName] = useState("");
  const [category, setCategory] = useState("");
  const [defaultUnit, setDefaultUnit] = useState("");
  const [defaultRate, setDefaultRate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const updateEntry = useUpdateMaterialLibraryEntry();

  const entries = libraryQuery.data ?? [];
  const cls = "mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createEntry.mutate(
      {
        raw_text: rawText.trim(),
        normalized_name: normalizedName.trim(),
        category: category.trim() || null,
        default_unit: defaultUnit.trim() || null,
        default_rate: defaultRate === "" ? null : Number(defaultRate),
      },
      {
        onSuccess: () => { setRawText(""); setNormalizedName(""); setCategory(""); setDefaultUnit(""); setDefaultRate(""); setFormOpen(false); },
        onError: () => setError("A mapping for this text may already exist."),
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="MATERIAL NORMALIZATION"
        title="Material library"
        description="Raw text seen on drawings, mapped to a clean material name — reused across every project."
        action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen((v) => !v)}>{formOpen ? "Close" : "Add mapping"}</Button> : null}
      />

      {formOpen ? (
        <form onSubmit={submit} className="grid gap-3 border-b border-[#e1d5bc] p-5 sm:grid-cols-2">
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Raw text *</span>
            <input className={cls} required value={rawText} onChange={(e) => setRawText(e.target.value)} placeholder="concrete gr45" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Normalized name *</span>
            <input className={cls} required value={normalizedName} onChange={(e) => setNormalizedName(e.target.value)} placeholder="Concrete Grade 45 (M45)" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Category</span>
            <input className={cls} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Concrete" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Default unit</span>
            <input className={cls} value={defaultUnit} onChange={(e) => setDefaultUnit(e.target.value)} placeholder="m3" />
          </label>
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">Default rate (PKR)</span>
            <input className={cls} type="number" step="any" value={defaultRate} onChange={(e) => setDefaultRate(e.target.value)} placeholder="18500" />
          </label>
          {error ? <div className="sm:col-span-2 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">{error}</div> : null}
          <div className="sm:col-span-2 flex justify-end">
            <Button type="submit" variant="primary" disabled={createEntry.isPending}>{createEntry.isPending ? "Saving…" : "Save mapping"}</Button>
          </div>
        </form>
      ) : null}

      {entries.length === 0 ? (
        <EmptyState icon="info" title="No mappings yet" description="Add entries here to speed up material normalization during parsing." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[520px] text-left">
            <thead className="bg-[#f5efe3]">
              <tr className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
                <th className="px-4 py-3">Raw text</th><th className="px-4 py-3">Normalized name</th><th className="px-4 py-3">Category</th><th className="px-4 py-3">Unit</th><th className="px-4 py-3 text-right">Default rate</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <MaterialLibraryRow
                  key={entry.id}
                  entry={entry}
                  canManage={canManage}
                  onSaveRate={(rate) => updateEntry.mutate({ entryId: entry.id, payload: { default_rate: rate } })}
                />
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </Panel>
  );
}

function MaterialLibraryRow({ entry, canManage, onSaveRate }: MaterialLibraryRowProps) {
  const [rate, setRate] = useState(entry.default_rate !== null ? String(entry.default_rate) : "");

  return (
    <tr className="border-t border-[#e1d5bc]">
      <td className="px-4 py-3 font-mono text-[10.5px] text-[#6b6152]">{entry.raw_text}</td>
      <td className="px-4 py-3 text-[11.5px] font-semibold text-[#191410]">{entry.normalized_name}</td>
      <td className="px-4 py-3 text-[11px] text-[#6b6152]">{entry.category ?? "—"}</td>
      <td className="px-4 py-3 text-[11px] text-[#6b6152]">{entry.default_unit ?? "—"}</td>
      <td className="px-4 py-3 text-right">
        {canManage ? (
          <input
            className="w-24 rounded-[6px] border border-[#d9ceb9] bg-white px-2 py-1 text-right text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            type="number"
            step="any"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            onBlur={() => onSaveRate(rate === "" ? null : Number(rate))}
          />
        ) : (
          <span className="font-mono text-[11px] text-[#191410]">{formatCurrency(entry.default_rate)}</span>
        )}
      </td>
    </tr>
  );
}