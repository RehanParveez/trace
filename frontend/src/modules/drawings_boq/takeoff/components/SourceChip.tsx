import { Badge } from "../../../organizations/components/OrganizationUi";
import type { FactSource } from "../types/takeoff.types";
import { pagesText, sourceGroups } from "../utils/projectFacts";
import type { ProjectDrawingNames } from "../utils/projectFacts";

interface Props {
  sources: FactSource[] | undefined;
  names: ProjectDrawingNames;
}

export function SourceChip(p: Props) {
  const groups = sourceGroups(p.sources, p.names);
  if (!groups.length) return null;
  return (
    <>
      {groups.map((g) => (
        <span key={g.drawingId} title={`${p.names[g.drawingId] ?? g.name}, ${pagesText(g.pages)}`} data-testid="source-chip" data-drawing={g.drawingId} data-pages={g.pages.join(",")}>
          <Badge tone="slate">{g.name} · {pagesText(g.pages)}</Badge>
        </span>
      ))}
    </>
  );
}
