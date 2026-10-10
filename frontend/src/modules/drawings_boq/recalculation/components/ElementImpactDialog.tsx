import { Badge, LoadingState, Modal, SectionLabel } from "../../../organizations/components/OrganizationUi";
import { getApiErrorCode, getApiErrorMessage } from "../../../identity";
import { useElementImpact } from "../hooks/useRecalculation";
import { useScaleT } from "../utils/useRecalculationT";

interface ElementImpactDialogProps {
  runId: string;
  elementId: string;
  onClose: () => void;
}

export function ElementImpactDialog({ runId, elementId, onClose }: ElementImpactDialogProps) {
  const t = useScaleT();
  const query = useElementImpact(runId, elementId);

  let body;
  if (query.isLoading) {
    body = <LoadingState label={t("scale.impact.loading", "Looking up what this element touches…")} />;
  } else if (query.isError || !query.data) {
    const code = getApiErrorCode(query.error);
    const message =
      code === "RUN_STATE_UNAVAILABLE"
        ? t("scale.impact.noState", "This run did not keep its overlap data, so the lookup is not available. Run the calculation again to enable it.")
        : code === "RUN_NOT_COMPLETED"
          ? t("scale.impact.notDone", "The lookup is available once the run has completed.")
          : code === "ELEMENT_NOT_IN_RUN"
            ? t("scale.impact.notInRun", "This element was not measured in this run.")
            : getApiErrorMessage(query.error, t("scale.impact.loadError", "Couldn't look up this element."));
    body = (
      <div role="alert" className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[12.5px] text-[var(--color-text-secondary)]">
        {message}
      </div>
    );
  } else {
    const d = query.data;
    const own = d.affected_ledger.filter((l) => l.element_id === d.element_id);
    const others = d.affected_ledger.filter((l) => l.element_id !== d.element_id);
    const nameOf = (id: string | null) => {
      if (id === null) return "—";
      const el = d.touching.find((x) => x.element_id === id);
      return el?.name || el?.ifc_type || id.slice(0, 8);
    };

    body = (
      <div className="space-y-6">
        <section>
          <SectionLabel>{t("scale.impact.touching", "Elements it overlaps")}</SectionLabel>
          {d.touching.length === 0 ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">{t("scale.impact.none", "It does not share volume with any other element.")}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[var(--color-surface-muted)]">
                  <tr>
                    {[t("scale.impact.colName", "Element"), t("scale.impact.colType", "Type"), t("scale.impact.colOverlap", "Shared volume (mm³)")].map((h) => (
                      <th key={h} className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.touching.map((el) => (
                    <tr key={el.element_id} className="border-t border-[var(--color-border)]">
                      <td className="px-3 py-2 text-[12px]">{el.name || el.ifc_global_id || el.element_id.slice(0, 8)}</td>
                      <td className="px-3 py-2 font-mono text-[11.5px] text-[var(--color-text-secondary)]">{el.ifc_type ?? "—"}</td>
                      <td className="px-3 py-2 text-right font-mono text-[12px]">
                        {el.overlap_mm3 === null ? "—" : Math.round(el.overlap_mm3).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <SectionLabel>{t("scale.impact.ledger", "Quantities that would change")}</SectionLabel>
          {d.affected_ledger.length === 0 ? (
            <div className="text-[12px] text-[var(--color-text-muted)]">{t("scale.impact.noLedger", "No ledger rows come from these elements.")}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left">
                <thead className="bg-[var(--color-surface-muted)]">
                  <tr>
                    {[t("scale.impact.colFrom", "From"), t("scale.impact.colWorkItem", "Work item"), t("scale.impact.colQty", "Quantity"), t("scale.impact.colUnit", "Unit")].map((h) => (
                      <th key={h} className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...own, ...others].map((l) => (
                    <tr key={l.ledger_id} className="border-t border-[var(--color-border)]">
                      <td className="px-3 py-2 text-[12px]">
                        {l.element_id === d.element_id ? <Badge tone="gold">{t("scale.impact.thisElement", "This element")}</Badge> : nameOf(l.element_id)}
                      </td>
                      <td className="px-3 py-2 font-mono text-[12px] font-semibold">{l.work_item_code}</td>
                      <td className="px-3 py-2 text-right font-mono text-[12px]">{String(l.quantity_net)}</td>
                      <td className="px-3 py-2 text-[12px]">{l.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {d.truncated ? (
          <div className="text-[11.5px] text-[var(--color-text-muted)]">
            {t("scale.impact.truncated", "This element touches a lot of others. Only the first part of the list is shown.")}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <Modal
      wide
      onClose={onClose}
      title={t("scale.impact.title", "What this element affects")}
      description={t("scale.impact.description", "Elements that share volume with it in this run, and the ledger rows that depend on them.")}
    >
      {body}
    </Modal>
  );
}
