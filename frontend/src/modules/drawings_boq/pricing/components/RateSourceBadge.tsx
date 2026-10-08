import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import { RATE_SOURCE_LABEL, rateSourceTone } from "../utils/pricing.utils";

export function RateSourceBadge({ source, hasRate = true }: { source: string | null | undefined; hasRate?: boolean }) {
  const { t } = useTranslation();
  if (!source && !hasRate) {
    return <Badge tone="red">{t("pricing.source.UNPRICED", "Unpriced")}</Badge>;
  }
  if (!source) {
    return <Badge tone="slate">{t("pricing.source.UNSOURCED", "No source")}</Badge>;
  }
  return <Badge tone={rateSourceTone(source)}>{t(`pricing.source.${source}`, RATE_SOURCE_LABEL[source] ?? source)}</Badge>;
}
