export type IncidentStatus = "Verified" | "Under review" | "Resolved" | "verified" | "review" | "resolved";

export interface Incident {
  id: string;
  latitude: number;
  longitude: number;
  lat?: number;
  lng?: number;
  confidence: number;
  detectorConfidence?: number;
  trackId?: string;
  sourceId?: string;
  sightingCount: number;
  sightings?: number;
  firstSeen: string;
  lastSeen: string;
  firstDetected?: string;
  lastDetected?: string;
  roadSegment: string;
  area: string;
  road?: string;
  status: IncidentStatus;
  severity: "High" | "Medium" | "Low";
  image?: string;
  representativeImage?: string;
  frame?: number | string;
  frameLabel?: string;
}

export type FilterKey = "all" | "verified" | "review" | "resolved" | "high";
