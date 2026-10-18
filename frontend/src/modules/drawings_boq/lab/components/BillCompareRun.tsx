import { useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useExportComparison } from "../hooks/useSteelCompare";
import { useCompareBill } from "../hooks/useRunCompare";
import type { BillClass, BillClasses, BillCompareResult } from "../types/billCompare.types";
import { applyClasses, classesStorageKey, compareErrorText, loadClasses, saveClasses, withClass } from "../utils/billCompare";
import { BillCompare } from "./BillCompare";

export function BillCompareRun({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const compare = useCompareBill(runId);
  const exporter = useExportComparison();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<BillCompareResult | undefined>();
  const [classes, setClasses] = useState<BillClasses>({});
  const [tolerance, setTolerance] = useState(5);
  const [error, setError] = useState<string | null>(null);

  const run = (f: File, tol: number, cls: BillClasses) => {
    setError(null);
    compare.mutate({ file: f, tolerancePct: tol, classes: cls }, {
      onSuccess: (r) => setResult(r),
      onError: (e) => setError(compareErrorText(e, t("drawings.billRun.failed", "Couldn't compare the bill. Nothing was changed."))),
    });
  };

  const upload = (f: File) => {
    const cls = loadClasses(classesStorageKey(runId, f.name));
    setFile(f);
    setClasses(cls);
    run(f, tolerance, cls);
  };

  const changeClass = (key: string, cls: BillClass | null, note: string) => {
    const next = withClass(classes, key, cls, note);
    setClasses(next);
    if (file) saveClasses(classesStorageKey(runId, file.name), next);
  };

  const changeTolerance = (pct: number) => {
    setTolerance(pct);
    if (file) run(file, pct, classes);
  };

  const download = () => {
    if (!result) return;
    exporter.mutate(applyClasses(result, classes), { onSuccess: (blob) => triggerBlobDownload(blob, "bill-comparison.xlsx") });
  };

  return (
    <div className="space-y-2 px-4 py-3" data-testid="bill-compare-run">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.billRun.intro", "Upload the QS bill. Each of its lines is set against the quantity this run worked out, and the whole is scored for how close it is.")}
      </p>
      <BillCompare result={result} classes={classes} busy={compare.isPending} error={error} tolerancePct={tolerance} onToleranceChange={changeTolerance} onUpload={upload} onClassChange={changeClass} onExport={download} />
    </div>
  );
}
