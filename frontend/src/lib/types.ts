import type { FilterKey, Incident, IncidentStatus } from "@/types/incident";

export type { FilterKey, Incident, IncidentStatus };

export function isHighPriority(i: Incident): boolean {
  return i.confidence >= 90 && i.status !== "Resolved" && i.status !== "resolved";
}

export function matchesFilter(i: Incident, f: FilterKey): boolean {
  switch (f) {
    case "all":
      return true;
    case "high":
      return isHighPriority(i);
    default:
      return i.status.toLowerCase() === f.toLowerCase();
  }
}

export const statusLabel: Record<string, string> = {
  verified: "Verified",
  Verified: "Verified",
  review: "Under review",
  "Under review": "Under review",
  resolved: "Resolved",
  Resolved: "Resolved",
};
