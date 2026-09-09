import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Button, EmptyState, ErrorState, Field, inputClass, LoadingState, Panel, PanelHeader, TableShell } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
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

  const stats = useMemo(() => {
    const priced = entries.filter((entry) => entry.default_rate !== null).length;
    const categories = new Set(
      entries.map((entry) => entry.category).filter((value): value is string => Boolean(value)),
    ).size;

    return { total: entries.length, priced, categories };
  }, [entries]);

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
        onError: (mutationError) =>
          setError(getApiErrorMessage(mutationError, "A mapping for this text may already exist.")),
      },
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="MATERIAL NORMALIZATION"
        title="Material library"
        description="Trace converts messy construction language on drawings into your organization's standard materials — reused across every project."
        action={canManage ? <Button variant="primary" size="sm" onClick={() => setFormOpen((v) => !v)}>{formOpen ? "Close" : "Add mapping"}</Button> : null}
      />

      {entries.length > 0 ? (
        <div className="flex flex-wrap gap-6 border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-4 sm:px-6">
          <div>
            <div className="font-[Archivo] text-[22px] font-bold tracking-[-0.02em] text-[var(--color-text-primary)]">{stats.total}</div>
            <div className="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Mappings</div>
          </div>

          <div>
            <div className="font-[Archivo] text-[22px] font-bold tracking-[-0.02em] text-[var(--color-text-primary)]">
              {stats.total === 0 ? "—" : `${Math.round((stats.priced / stats.total) * 100)}%`}
            </div>
            <div className="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Priced automatically</div>
          </div>

          <div>
            <div className="font-[Archivo] text-[22px] font-bold tracking-[-0.02em] text-[var(--color-text-primary)]">{stats.categories}</div>
            <div className="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">Categories</div>
          </div>
        </div>
      ) : null}

      {formOpen ? (
        <form onSubmit={submit} className="grid gap-4 border-b border-[var(--color-border)] p-5 sm:grid-cols-2">
          <Field label="Raw text">
            <input className={inputClass} required value={rawText} onChange={(e) => setRawText(e.target.value)} placeholder="concrete gr45" />
          </Field>

          <Field label="Normalized name">
            <input className={inputClass} required value={normalizedName} onChange={(e) => setNormalizedName(e.target.value)} placeholder="Concrete Grade 45 (M45)" />
          </Field>

          <Field label="Category">
            <input className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Concrete" />
          </Field>

          <Field label="Default unit">
            <input className={inputClass} value={defaultUnit} onChange={(e) => setDefaultUnit(e.target.value)} placeholder="m3" />
          </Field>

          <Field label="Default rate (PKR)">
            <input className={inputClass} type="number" step="any" value={defaultRate} onChange={(e) => setDefaultRate(e.target.value)} placeholder="18500" />
          </Field>

          {error ? (
            <div className="sm:col-span-2 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div>
          ) : null}

          <div className="sm:col-span-2 flex justify-end">
            <Button type="submit" variant="primary" disabled={createEntry.isPending}>{createEntry.isPending ? "Saving…" : "Save mapping"}</Button>
          </div>
        </form>
      ) : null}

      {libraryQuery.isLoading ? (
        <LoadingState label="Loading material library…" />
      ) : libraryQuery.isError ? (
        <ErrorState title="We couldn't load the material library" onRetry={() => void libraryQuery.refetch()} />
      ) : entries.length === 0 ? (
        <EmptyState icon="info" title="No mappings yet" description="Add entries here to speed up material normalization during parsing." />
      ) : (
        <TableShell>
          <table className="w-full min-w-[560px] text-left">
            <thead className="bg-[var(--color-surface-muted)]">
              <tr className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Raw drawing text</th>
                <th className="px-4 py-3">Trace material</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Unit</th>
                <th className="px-4 py-3 text-right">Default rate</th>
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
    <tr className="border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)]">
      <td className="px-4 py-3 font-mono text-[12px] text-[var(--color-text-secondary)]">{entry.raw_text}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-trace-gold-dark)]">→</span>
          <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">{entry.normalized_name}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-[12px] text-[var(--color-text-secondary)]">{entry.category ?? "—"}</td>
      <td className="px-4 py-3 text-[12px] text-[var(--color-text-secondary)]">{entry.default_unit ?? "—"}</td>
      <td className="px-4 py-3 text-right">
        {canManage ? (
          <input
            className="w-24 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-right text-[12px] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-trace-gold-dark)]"
            type="number"
            step="any"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            onBlur={() => onSaveRate(rate === "" ? null : Number(rate))}
          />
        ) : (
          <span className="font-mono text-[12px] text-[var(--color-text-primary)]">{formatCurrency(entry.default_rate)}</span>
        )}
      </td>
    </tr>
  );
}