import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { fieldChange } from "../utils/bbsAudit";
import type { BbsVersionDiff } from "../types/bbsAudit.types";

const SHOWN = 10;

export function BbsDiffPanel({ diff }: { diff: BbsVersionDiff }) {
  const { t } = useTranslation();
  const c = diff.counts;
  return (
    <div className="space-y-2 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3" data-testid="bbs-diff-panel">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">
          {t("bbs.diff.title", "Changes from version {{from}} to version {{to}}", { from: diff.from_version ?? "?", to: diff.to_version ?? "?" })}
        </span>
        <Badge tone="green">{t("bbs.diff.added", "{{n}} added", { n: c.added })}</Badge>
        <Badge tone="red">{t("bbs.diff.removed", "{{n}} removed", { n: c.removed })}</Badge>
        <Badge tone="gold">{t("bbs.diff.changed", "{{n}} changed", { n: c.changed })}</Badge>
        <Badge tone="blue">{t("bbs.diff.same", "{{n}} unchanged", { n: c.same })}</Badge>
      </div>
      {diff.changed.slice(0, SHOWN).map((row) => (
        <div key={row.key} className="text-[12px] text-[var(--color-text-secondary)]">
          <span className="font-mono">{row.key}</span>
          {": "}
          {Object.entries(row.fields).map(([name, change]) => `${name} ${fieldChange(change)}`).join("; ")}
        </div>
      ))}
      {diff.added.slice(0, SHOWN).map((k) => <div key={`a-${k}`} className="font-mono text-[12px] text-[var(--color-success)]">+ {k}</div>)}
      {diff.removed.slice(0, SHOWN).map((k) => <div key={`r-${k}`} className="font-mono text-[12px] text-[var(--color-danger)]">− {k}</div>)}
    </div>
  );
}
