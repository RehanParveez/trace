import { useTranslation } from "react-i18next";
import type { AuditRun } from "../types/bbsAudit.types";
import { readDiff } from "../utils/bbsAudit";
import { BbsDiffPanel } from "./BbsDiffPanel";

export function VersionDiff({ run, version }: { run: AuditRun | null | undefined; version: number }) {
  const { t } = useTranslation();
  const diff = readDiff(run);
  if (!diff) {
    return <p className="text-[12.5px] text-[var(--color-text-muted)]">{version <= 1
      ? t("bbs.diff.first", "This is the first version of the schedule, so there is nothing to compare it with.")
      : t("bbs.diff.notRun", "Run the audit on this version to see the rows that changed from the version before.")}</p>;
  }
  return <BbsDiffPanel diff={diff} />;
}
