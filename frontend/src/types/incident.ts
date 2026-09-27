export type IncidentStatus = "Verified" | "Under review" | "Resolved";

export interface Incident {
  id: string;
  latitude: number;
  longitude: number;
  confidence: number;
  detectorConfidence?: number;
  trackId?: string;
  sourceId?: string;
  sightingCount: number;
  firstSeen: string;
  lastSeen: string;
  roadSegment: string;
  area: string;
  status: IncidentStatus;
  severity: "High" | "Medium" | "Low";
  image?: string;
}
