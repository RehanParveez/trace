import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, useToast } from "../../../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../../../identity";
import { triggerBlobDownload } from "../../../utils/drawings-boq.utils";
import { schedulesApi } from "../api/schedules.api";

export function BookExportButtons({ bookId, code, version }: { bookId: string; code: string; version: number }) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [busy, setBusy] = useState<"csv" | "xlsx" | null>(null);

  async function download(format: "csv" | "xlsx") {
    setBusy(format);
    try {
      const blob = await schedulesApi.exportBook(bookId, format);
      triggerBlobDownload(blob, `${code}_v${version}.${format}`);
    } catch (e) {
      showToast({ tone: "error", title: t("schedules.export.error", "The export failed"), description: getApiErrorMessage(e, t("schedules.export.errorDesc", "Please try again.")) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Button variant="secondary" size="sm" disabled={busy !== null} onClick={() => void download("xlsx")}>{busy === "xlsx" ? t("common.loading", "Loading…") : t("schedules.export.xlsx", "Export Excel")}</Button>
      <Button variant="secondary" size="sm" disabled={busy !== null} onClick={() => void download("csv")}>{busy === "csv" ? t("common.loading", "Loading…") : t("schedules.export.csv", "Export CSV")}</Button>
    </>
  );
}
