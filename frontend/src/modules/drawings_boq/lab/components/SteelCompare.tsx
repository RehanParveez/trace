import { useState } from "react";
import { useTranslation } from "react-i18next";
import { triggerBlobDownload } from "../../utils/drawings-boq.utils";
import { useCompareSteel, useExportComparison } from "../hooks/useSteelCompare";
import type { BillClass, BillClasses, BillCompareResult } from "../types/billCompare.types";
import { applyClasses, classesStorageKey, compareErrorText, loadClasses, saveClasses, withClass } from "../utils/billCompare";
import { BillCompare } from "./BillCompare";

export function SteelCompare({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const compare = useCompareSteel(runId);
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
      onError: (e) => setError(compareErrorText(e, t("drawings.steel.failed", "Couldn't compare the steel. Nothing was changed."))),
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
    exporter.mutate(applyClasses(result, classes), { onSuccess: (blob) => triggerBlobDownload(blob, "steel-comparison.xlsx") });
  };

  return (
    <div className="space-y-2 px-4 py-3" data-testid="steel-compare">
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("drawings.steel.intro", "Upload the QS workbook. Its Steel Summary sheet is read group by group (columns, slab, lintels...) and floor by floor, and set against the steel this run worked out.")}
      </p>
      <BillCompare result={result} classes={classes} busy={compare.isPending} error={error} tolerancePct={tolerance} onToleranceChange={changeTolerance} onUpload={upload} onClassChange={changeClass} onExport={download} />
    </div>
  );
}
