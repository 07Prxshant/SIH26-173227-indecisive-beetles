import { useEffect, useState } from "react";
import { mockIncidents } from "@/map/mock-incidents";
import type { Incident, IncidentStatus } from "@/types/incident";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ApiIncident = {
  incident_id: string;
  latitude: number;
  longitude: number;
  road_segment_id: string;
  confidence: number;
  sighting_count: number;
  first_seen: string;
  last_seen: string;
  status: "candidate" | "verified" | "resolved";
  representative_image?: string | null;
};

const formatSeenAt = (value: string) =>
  new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const statusFor = (status: ApiIncident["status"]): IncidentStatus => {
  if (status === "verified") return "Verified";
  if (status === "resolved") return "Resolved";
  return "Under review";
};

export const toDashboardIncident = (incident: ApiIncident): Incident => {
  const confidence = Math.round(incident.confidence * 100);
  return {
    id: incident.incident_id,
    latitude: incident.latitude,
    longitude: incident.longitude,
    confidence,
    sightingCount: incident.sighting_count,
    firstSeen: formatSeenAt(incident.first_seen),
    lastSeen: formatSeenAt(incident.last_seen),
    roadSegment: incident.road_segment_id,
    area: incident.road_segment_id,
    status: statusFor(incident.status),
    severity: confidence >= 90 ? "High" : confidence >= 70 ? "Medium" : "Low",
    image: incident.representative_image ?? undefined,
  };
};

export function useLiveIncidents(): Incident[] {
  const [incidents, setIncidents] = useState<Incident[]>(mockIncidents);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    const fetchVerifiedIncidents = () => {
      void fetch(`${apiBaseUrl}/incidents?status=verified`)
        .then((response) => (response.ok ? response.json() : Promise.reject(response)))
        .then((payload: { items: ApiIncident[] }) => {
          if (active) setIncidents(payload.items.map(toDashboardIncident));
        })
        .catch(() => undefined);
    };

    fetchVerifiedIncidents();

    const connectWebSocket = () => {
      if (!active) return;
      const websocketUrl = `${apiBaseUrl.replace(/^http/, "ws")}/live-feed`;
      socket = new WebSocket(websocketUrl);

      socket.onopen = () => {
        console.log("[Frontend] WebSocket connected to live feed");
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as { type?: string; incident?: ApiIncident };
          if (message.type !== "incident_created" || !message.incident) return;
          const incoming = toDashboardIncident(message.incident);
          console.log("[Frontend] Incident displayed", incoming);
          setIncidents((current) => [
            incoming,
            ...current.filter((item) => item.id !== incoming.id),
          ]);
        } catch (err) {
          console.warn("[Frontend] Failed to parse WebSocket message:", err);
        }
      };

      socket.onclose = () => {
        if (!active) return;
        console.warn("[Frontend] WebSocket disconnected. Attempting reconnect in 3s...");
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };

      socket.onerror = () => {
        if (socket) socket.close();
      };
    };

    connectWebSocket();

    return () => {
      active = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socket) socket.close();
    };
  }, []);

  return incidents;
}
