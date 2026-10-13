import { useCalculationRun } from "../hooks";
import type { Drawing } from "../types/drawings-boq.types";
import { RunScope } from "./RunScope";

interface BOQSourceDrawingsProps {
  runId: string | null | undefined;
  drawings: Drawing[];
}

export function BOQSourceDrawings({ runId, drawings }: BOQSourceDrawingsProps) {
  const runQuery = useCalculationRun(runId ?? undefined);

  if (!runId) {
    return null;
  }

  return <RunScope run={runQuery.data} drawings={drawings} />;
}
