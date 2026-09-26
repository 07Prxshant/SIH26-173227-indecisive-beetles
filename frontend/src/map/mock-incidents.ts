import type { Incident } from "@/types/incident";
import evidenceImage from "@/assets/pothole-evidence.jpg";

// Illustrative locations and observations for the frontend demonstration only.
export const mockIncidents: Incident[] = [
  { id: "INC-2048", latitude: 12.9754, longitude: 77.6022, confidence: 98, sightingCount: 12, firstSeen: "26 Sep 2026, 08:42", lastSeen: "26 Sep 2026, 12:18", roadSegment: "Mahatma Gandhi Road · eastbound", area: "MG Road", status: "Verified", severity: "High", image: evidenceImage },
  { id: "INC-2047", latitude: 12.9832, longitude: 77.6077, confidence: 94, sightingCount: 8, firstSeen: "26 Sep 2026, 07:16", lastSeen: "26 Sep 2026, 11:53", roadSegment: "Brigade Road · northbound", area: "Brigade Road", status: "Verified", severity: "High" },
  { id: "INC-2046", latitude: 12.9711, longitude: 77.5935, confidence: 89, sightingCount: 6, firstSeen: "25 Sep 2026, 17:05", lastSeen: "26 Sep 2026, 10:34", roadSegment: "Residency Road · westbound", area: "Residency Road", status: "Verified", severity: "Medium" },
  { id: "INC-2045", latitude: 12.9882, longitude: 77.5948, confidence: 83, sightingCount: 5, firstSeen: "25 Sep 2026, 14:22", lastSeen: "26 Sep 2026, 09:11", roadSegment: "Queens Road · southbound", area: "Queens Road", status: "Verified", severity: "Medium" },
  { id: "INC-2044", latitude: 12.9654, longitude: 77.6066, confidence: 76, sightingCount: 3, firstSeen: "25 Sep 2026, 12:40", lastSeen: "26 Sep 2026, 08:05", roadSegment: "Richmond Road · eastbound", area: "Richmond Road", status: "Under review", severity: "Medium" },
  { id: "INC-2043", latitude: 12.9925, longitude: 77.6153, confidence: 68, sightingCount: 2, firstSeen: "24 Sep 2026, 18:33", lastSeen: "25 Sep 2026, 16:20", roadSegment: "Cunningham Road · northbound", area: "Cunningham Road", status: "Under review", severity: "Low" },
  { id: "INC-2042", latitude: 12.9629, longitude: 77.5898, confidence: 92, sightingCount: 7, firstSeen: "23 Sep 2026, 09:14", lastSeen: "24 Sep 2026, 15:02", roadSegment: "Lalbagh Road · southbound", area: "Lalbagh Road", status: "Resolved", severity: "High" },
];
