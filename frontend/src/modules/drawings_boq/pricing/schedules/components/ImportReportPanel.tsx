import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, Panel, PanelHeader } from "../../../../organizations/components/OrganizationUi";
import type { ImportReport } from "../types/schedules.types";
import { CHECK_STATUS_LABEL, checkTone } from "../utils/schedules.utils";

export function ImportReportPanel({ report }: { report: ImportReport }) {
  const { t } = useTranslation();
  const [showLines, setShowLines] = useState(false);
  const tone = report.status === "PASS" ? "green" : report.status === "FAIL" ? "red" : "gold";
  const label =
    report.status === "PASS" ? t("schedules.report.pass", "All checks passed")
      : report.status === "FAIL" ? t("schedules.report.fail", "Some checks failed")
        : t("schedules.report.warn", "Passed with things to look at");

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("schedules.report.eyebrow", "AUTOMATIC CHECKS")}
        title={t("schedules.report.title", "How well the file was read")}
        description={t(
          "schedules.report.desc",
          "Every number is read twice and compared, pages and units are counted, and rates far from their neighbours are flagged. These do not replace looking at the page: the spot-check rows below are for that.",
        )}
        action={<Badge tone={tone}>{label}</Badge>}
      />
      <ul className="divide-y divide-[var(--color-border)]">
        {report.checks.map((check) => (
          <li key={check.code} className="flex flex-wrap items-start justify-between gap-3 px-5 py-3">
            <div className="min-w-0">
              <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">{check.label}</div>
              <div className="mt-0.5 text-[12.5px] leading-5 text-[var(--color-text-secondary)]">{check.detail}</div>
            </div>
            <Badge tone={checkTone(check.status)}>{t(`schedules.check.${check.status}`, CHECK_STATUS_LABEL[check.status])}</Badge>
          </li>
        ))}
      </ul>
      {report.unparsed_sample.length > 0 ? (
        <div className="border-t border-[var(--color-border)] px-5 py-3">
          <Button variant="ghost" size="sm" onClick={() => setShowLines((v) => !v)}>
            {showLines
              ? t("schedules.report.hideLines", "Hide lines that were not read")
              : t("schedules.report.showLines", "Show lines that looked like rows but were not read ({{n}})", { n: report.unparsed_sample.length })}
          </Button>
          {showLines ? (
            <ul className="mt-3 space-y-1 font-mono text-[11.5px] text-[var(--color-text-secondary)]">
              {report.unparsed_sample.map((line, i) => (
                <li key={`${line.page}-${line.line}-${i}`}>
                  <span className="text-[var(--color-text-muted)]">p{line.page ?? "?"}:{line.line ?? "?"}</span> {line.text}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </Panel>
  );
}
