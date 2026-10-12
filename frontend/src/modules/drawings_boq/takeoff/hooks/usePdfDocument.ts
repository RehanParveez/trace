import { useEffect, useState } from "react";
import * as pdfjs from "pdfjs-dist/legacy/build/pdf.mjs";
import type { PDFDocumentProxy } from "pdfjs-dist";
import pdfWorkerUrl from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";
import { drawingsBoqApi } from "../../api/drawings-boq.api";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export type PdfLoadState =
  | { status: "loading"; progress: number }
  | { status: "ready"; doc: PDFDocumentProxy }
  | { status: "error"; error: unknown };

export function usePdfDocument(drawingId: string | undefined): PdfLoadState {
  const [state, setState] = useState<PdfLoadState>({ status: "loading", progress: 0 });

  useEffect(() => {
    if (!drawingId) return;
    let cancelled = false;
    let task: ReturnType<typeof pdfjs.getDocument> | null = null;
    setState({ status: "loading", progress: 0 });
    (async () => {
      try {
        const blob = await drawingsBoqApi.getDrawingFile(drawingId);
        if (cancelled) return;
        const data = new Uint8Array(await blob.arrayBuffer());
        if (cancelled) return;
        task = pdfjs.getDocument({ data });
        task.onProgress = (p: { loaded: number; total: number }) => {
          if (!cancelled && p.total) setState({ status: "loading", progress: Math.min(1, p.loaded / p.total) });
        };
        const doc = await task.promise;
        if (cancelled) {
          void doc.destroy();
          return;
        }
        setState({ status: "ready", doc });
      } catch (error) {
        if (!cancelled) setState({ status: "error", error });
      }
    })();
    return () => {
      cancelled = true;
      if (task) void task.destroy();
    };
  }, [drawingId]);

  return state;
}