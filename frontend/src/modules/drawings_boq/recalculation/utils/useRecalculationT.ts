import { useCallback } from "react";
import { useTranslation } from "react-i18next";

export type Translate = (key: string, fallback: string, options?: Record<string, unknown>) => string;

export function useScaleT(): Translate {
  const { t } = useTranslation();
  return useCallback(
    (key, fallback, options) => String(t(key, { defaultValue: fallback, ...(options ?? {}) })),
    [t],
  );
}