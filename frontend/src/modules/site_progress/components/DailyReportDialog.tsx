import { Badge, Button, ErrorState, LoadingState, Modal } from "../../organizations/components/OrganizationUi";
import type { ReactNode } from "react";
import { useDailyReport } from "../hooks";
import { formatLogDate } from "../utils/site-progress.utils";
import { useTranslation } from "react-i18next";

interface DailyReportDialogProps {
  projectId: string;
  reportDate: string;
  onClose: () => void;
}

const PRINT_CSS = `@media print {
  body * { visibility: hidden !important; }
  #daily-report-print, #daily-report-print * { visibility: visible !important; }
  #daily-report-print { position: absolute; left: 0; top: 0; width: 100%; padding: 16px; }
  .no-print { display: none !important; }
}`;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="break-inside-avoid">
      <h4 className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{title}</h4>
      {children}
    </section>
  );
}

export function DailyReportDialog({ projectId, reportDate, onClose }: DailyReportDialogProps) {
  const { t } = useTranslation();
  const reportQuery = useDailyReport(projectId, reportDate);
  const report = reportQuery.data;

  function whatsappText(): string {
    if (!report) return "";
    const lines: string[] = [`*${report.project_name}* — ${formatLogDate(report.report_date)}`];
    if (report.weather) lines.push(`${t("siteProgress.report.weather")}: ${report.weather}`);
    lines.push(`${t("siteProgress.report.manpower")}: ${Number(report.manpower_total) || report.reported_workforce || 0}`);
    if (report.work_done.length) lines.push("", `*${t("siteProgress.report.workDone")}*`, ...report.work_done.map((x) => `• ${x}`));
    if (report.deliveries.length) lines.push("", `*${t("siteProgress.report.deliveries")}*`, ...report.deliveries.map((d) => `• ${d.material_name}: ${d.quantity} ${d.unit}`));
    if (report.blockers.length) lines.push("", `*${t("siteProgress.report.blockers")}*`, ...report.blockers.map((x) => `• ${x}`));
    if (report.client_instructions.length) lines.push("", `*${t("siteProgress.report.clientInstructions")}*`, ...report.client_instructions.map((x) => `• ${x}`));
    return lines.join("\n");
  }

  return (
    <Modal title={t("siteProgress.report.title")} description={report ? formatLogDate(report.report_date) : undefined} onClose={onClose} wide>
      <style>{PRINT_CSS}</style>
      {reportQuery.isLoading ? (
        <LoadingState label={t("common.loading")} />
      ) : reportQuery.isError || !report ? (
        <ErrorState title={t("siteProgress.report.loadError")} onRetry={() => void reportQuery.refetch()} />
      ) : (
        <div className="space-y-5">
          <div id="daily-report-print" className="space-y-5">
            <div>
              <div className="text-[16px] font-bold text-[var(--color-text-primary)]">{report.project_name}</div>
              <div className="text-[12.5px] text-[var(--color-text-secondary)]">
                {t("siteProgress.report.dailyReport")} · {formatLogDate(report.report_date)}
                {report.weather ? ` · ${report.weather}` : ""}
              </div>
            </div>

            <Section title={t("siteProgress.report.manpower")}>
              {report.manpower.length === 0 && report.reported_workforce === null ? (
                <p className="text-[12.5px] text-[var(--color-text-secondary)]">{t("siteProgress.report.noManpower")}</p>
              ) : (
                <>
                  <div className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                    {Number(report.manpower_total) > 0 ? Number(report.manpower_total) : report.reported_workforce}
                    {report.manpower.length > 0 ? <span className="ml-2 font-normal text-[var(--color-text-secondary)]">({report.manpower.map((m) => `${Number(m.units)} ${m.trade}`).join(", ")})</span> : null}
                  </div>
                  {report.manpower_mismatch ? (
                    <div className="no-print mt-1"><Badge tone="red">{t("siteProgress.report.mismatch", { reported: report.reported_workforce ?? 0, attendance: Number(report.manpower_total) })}</Badge></div>
                  ) : null}
                </>
              )}
            </Section>

            {report.work_done.length > 0 ? (
              <Section title={t("siteProgress.report.workDone")}>
                <ul className="list-disc space-y-0.5 pl-5 text-[13px] text-[var(--color-text-primary)]">{report.work_done.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Section>
            ) : null}

            {report.deliveries.length > 0 ? (
              <Section title={t("siteProgress.report.deliveries")}>
                <ul className="space-y-0.5 text-[13px] text-[var(--color-text-primary)]">
                  {report.deliveries.map((d, i) => (
                    <li key={i}>{d.material_name}: <strong>{Number(d.quantity)} {d.unit}</strong>{d.supplier_name ? ` — ${d.supplier_name}` : ""}{d.invoice_number ? ` (#${d.invoice_number})` : ""}</li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {report.issues.length > 0 ? (
              <Section title={t("siteProgress.report.materialsUsed")}>
                <ul className="space-y-0.5 text-[13px] text-[var(--color-text-primary)]">
                  {report.issues.map((m, i) => (
                    <li key={i}>
                      {m.material_name}: <strong>{Number(m.quantity)} {m.unit}</strong>
                      {m.issue_type === "WASTAGE" ? ` — ${t("siteProgress.report.wastage")}` : m.issued_to ? ` → ${m.issued_to}` : ""}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {report.blockers.length > 0 ? (
              <Section title={t("siteProgress.report.blockers")}>
                <ul className="list-disc space-y-0.5 pl-5 text-[13px] text-[var(--color-text-primary)]">{report.blockers.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Section>
            ) : null}

            {report.client_instructions.length > 0 ? (
              <Section title={t("siteProgress.report.clientInstructions")}>
                <ul className="list-disc space-y-0.5 pl-5 text-[13px] text-[var(--color-text-primary)]">{report.client_instructions.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Section>
            ) : null}

            {report.notes.length > 0 ? (
              <Section title={t("siteProgress.report.notes")}>
                <ul className="list-disc space-y-0.5 pl-5 text-[13px] text-[var(--color-text-primary)]">{report.notes.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Section>
            ) : null}

            {report.photos.length > 0 ? (
              <Section title={t("siteProgress.report.photos", { count: report.photo_count })}>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                  {report.photos.map((photo) => (
                    <figure key={photo.photo_id} className="overflow-hidden rounded-[8px] border border-[var(--color-border)]">
                      <img src={photo.photo_url} alt={photo.caption ?? photo.location_text ?? ""} className="h-24 w-full object-cover" loading="lazy" />
                      {photo.location_text || photo.caption ? <figcaption className="truncate px-1.5 py-1 text-[10.5px] text-[var(--color-text-secondary)]">{photo.location_text ?? photo.caption}</figcaption> : null}
                    </figure>
                  ))}
                </div>
                {report.photo_count > report.photos.length ? (
                  <p className="mt-1 text-[11px] text-[var(--color-text-secondary)]">{t("siteProgress.report.morePhotos", { count: report.photo_count - report.photos.length })}</p>
                ) : null}
              </Section>
            ) : null}
          </div>

          <div className="no-print flex flex-wrap justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <Button variant="ghost" onClick={onClose}>{t("common.close", "Close")}</Button>
            <Button variant="secondary" onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(whatsappText())}`, "_blank", "noopener")}>{t("siteProgress.report.shareWhatsapp")}</Button>
            <Button variant="primary" onClick={() => window.print()}>{t("siteProgress.report.print")}</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}