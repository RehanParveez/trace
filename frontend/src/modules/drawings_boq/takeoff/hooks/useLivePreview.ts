import { useEffect, useRef, useState } from "react";
import { takeoffApi } from "../api/takeoff.api";
import type { PreviewRequest, PreviewResult } from "../types/takeoff.types";

export type PreviewState =
  | { status: "idle" }
  | { status: "loading"; last: PreviewResult | null }
  | { status: "ready"; result: PreviewResult }
  | { status: "failed"; message: string };

export function useLivePreview(request: PreviewRequest | null, delayMs = 250): PreviewState {
  const [state, setState] = useState<PreviewState>({ status: "idle" });
  const seq = useRef(0);
  const lastGood = useRef<PreviewResult | null>(null);
  const key = request ? JSON.stringify(request) : "";

  useEffect(() => {
    if (!request) {
      seq.current += 1;
      setState({ status: "idle" });
      return;
    }
    const mine = ++seq.current;
    const controller = new AbortController();
    setState({ status: "loading", last: lastGood.current });
    const timer = window.setTimeout(async () => {
      try {
        const result = await takeoffApi.preview(request, controller.signal);
        if (seq.current !== mine) return;
        lastGood.current = result.ok ? result : null;
        setState({ status: "ready", result });
      } catch (error) {
        if (seq.current !== mine || controller.signal.aborted) return;
        setState({ status: "failed", message: error instanceof Error ? error.message : "The preview could not be calculated." });
      }
    }, delayMs);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };

  }, [key, delayMs]);

  return state;
}
