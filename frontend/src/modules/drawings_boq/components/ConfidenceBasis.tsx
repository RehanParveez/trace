import { useTranslation } from "react-i18next";
import { geometryBasis, geometrySourceLabel } from "../utils/trust";

export function ConfidenceBasis({ trace }: { trace: unknown }) {
  const { t } = useTranslation();
  const basis = geometryBasis(trace);
  if (!basis) {
    return null;
  }
  return (
    <div className="text-[11px] text-[var(--color-text-muted)]">
      {t("boq.trust.basis", "Confidence is based on")}: {geometrySourceLabel(basis.key, (key, fallback) => t(key, fallback))}
      {basis.factor !== null ? ` (× ${basis.factor.toFixed(2)})` : ""}
    </div>
  );
}
