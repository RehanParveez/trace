import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { BASIS_TEXT, basisOfRoute } from "../utils/passes";
import type { Basis } from "../utils/passes";

interface Props {
  route?: string;
  basis?: Basis;
  title?: string;
}

const TONE: Record<Basis, "green" | "blue" | "gold"> = { DRAWING: "green", TYPED: "blue", ASSUMED: "gold" };
const LABEL: Record<Basis, string> = { DRAWING: "Drawing", TYPED: "Typed", ASSUMED: "Assumed" };

export function BasisChip({ route, basis, title }: Props) {
  const { t } = useTranslation();
  const b = basis ?? basisOfRoute(route);
  return (
    <span title={title ?? t(`boq.takeoff.passes.basisText.${b}`, BASIS_TEXT[b])} data-testid="basis-chip" data-basis={b}>
      <Badge tone={TONE[b]}>{t(`boq.takeoff.passes.basis.${b}`, LABEL[b])}</Badge>
    </span>
  );
}
