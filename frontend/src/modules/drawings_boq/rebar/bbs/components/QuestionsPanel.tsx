import { useTranslation } from "react-i18next";
import { Button, EmptyState } from "../../../../organizations/components/OrganizationUi";
import type { ReportQuestion } from "../types/bbsReport.types";

interface QuestionsPanelProps {
  items: ReportQuestion[];
  copied: number | "all" | null;
  onCopy: (which: number | "all") => void;
}

export function QuestionsPanel({ items, copied, onCopy }: QuestionsPanelProps) {
  const { t } = useTranslation();
  if (items.length === 0) return <EmptyState icon="info" title={t("bbs.questions.none", "No question is open")} description={t("bbs.questions.noneDesc", "Every finding that asked something has been decided.")} />;
  return (
    <div className="space-y-3" data-testid="bbs-questions">
      <div className="flex items-center gap-2">
        <span className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">{t("bbs.questions.title", "{{n}} open question(s) for the engineer and the QS", { n: items.length })}</span>
        <div className="ml-auto"><Button variant="secondary" size="sm" onClick={() => onCopy("all")}>{copied === "all" ? t("bbs.copied", "Copied") : t("bbs.questions.copyAll", "Copy all")}</Button></div>
      </div>
      <ol className="space-y-2">
        {items.map((q) => (
          <li key={q.finding_id} className="flex items-start gap-3 rounded-[8px] border border-[var(--color-border)] px-3 py-2">
            <span className="font-mono text-[12px] font-semibold text-[var(--color-text-muted)]">Q{q.no}</span>
            <div className="min-w-0 flex-1">
              <div className="text-[11.5px] text-[var(--color-text-muted)]">{q.where} · F{q.finding_no}</div>
              <div className="text-[12.5px] text-[var(--color-text-primary)]">{q.question}</div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => onCopy(q.no)}>{copied === q.no ? t("bbs.copied", "Copied") : t("bbs.copy", "Copy")}</Button>
          </li>
        ))}
      </ol>
    </div>
  );
}
