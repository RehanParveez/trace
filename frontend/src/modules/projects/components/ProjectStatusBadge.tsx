import { Badge } from "../../organizations/components/OrganizationUi";
import type { ProjectStatus } from "../types/project.types";
import {formatProjectStatus, getProjectStatusTone,
} from "../utils/project.utils";

interface ProjectStatusBadgeProps {
  status: ProjectStatus;
}

export function ProjectStatusBadge({
  status,
}: ProjectStatusBadgeProps) {
  return (
    <Badge tone={getProjectStatusTone(status)}>
      {formatProjectStatus(status)}
    </Badge>
  );
}