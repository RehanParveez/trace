import type { BOQLifecycle, BOQVersion } from "../../api/types";

type VersionLike = Pick<BOQVersion, "origin" | "lifecycle">;

const LOCKED: ReadonlySet<BOQLifecycle> = new Set([
  "CALCULATING",
  "APPROVED",
  "ISSUED",
  "SUPERSEDED",
  "ARCHIVED",
]);

export function isEngine(version: VersionLike): boolean {
  return version.origin === "ENGINE";
}

export function isLocked(version: VersionLike): boolean {
  return isEngine(version) && LOCKED.has(version.lifecycle);
}

export type VersionAction = "submit" | "reopen" | "approve" | "issue" | "archive";

export function availableActions(version: VersionLike): VersionAction[] {
  if (!isEngine(version)) return [];
  switch (version.lifecycle) {
    case "CALCULATED":
      return ["submit", "archive"];
    case "UNDER_REVIEW":
      return ["reopen", "approve", "archive"];
    case "APPROVED":
      return ["issue", "archive"];
    case "ISSUED":
    case "SUPERSEDED":
    case "DRAFT":
      return ["archive"];
    default:
      return []; 
  }
}

export function lifecycleTone(
  lifecycle: BOQLifecycle,
): "neutral" | "good" | "warn" | "bad" {
  switch (lifecycle) {
    case "APPROVED":
    case "ISSUED":
      return "good";
    case "CALCULATING":
    case "UNDER_REVIEW":
      return "warn";
    case "ARCHIVED":
    case "SUPERSEDED":
      return "bad";
    default:
      return "neutral";
  }
}