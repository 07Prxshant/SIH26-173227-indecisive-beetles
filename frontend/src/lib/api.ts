import { apiBaseUrl, toDashboardIncident } from "./incident-api";
import type { Incident } from "@/types/incident";

export async function getIncidents(): Promise<Incident[]> {
  try {
    const res = await fetch(`${apiBaseUrl}/incidents`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []).map(toDashboardIncident);
  } catch {
    return [];
  }
}

export async function updateStatus(id: string, status: string): Promise<boolean> {
  try {
    const res = await fetch(`${apiBaseUrl}/incidents/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function searchLocations(query: string): Promise<string[]> {
  if (!query || query.length < 2) return [];
  const sample = [
    "Connaught Place, Delhi",
    "Sector 52, Noida",
    "MG Road, Bengaluru",
    "Hitech City, Hyderabad",
    "Marine Drive, Mumbai",
    "Kota City Center, Kota",
  ];
  return sample.filter((s) => s.toLowerCase().includes(query.toLowerCase()));
}

export async function uploadVideo(
  file: File,
  location?: string,
  gpsFile?: File | null
): Promise<{ incident: Incident }> {
  const formData = new FormData();
  formData.append("video", file);
  formData.append("file", file);
  if (location) formData.append("user_location", location);
  if (gpsFile) formData.append("gps", gpsFile);

  const res = await fetch(`${apiBaseUrl}/videos/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Upload failed with status ${res.status}`);
  }

  const data = await res.json();
  const raw = (data.fused_incidents || data.incidents || [])[0];
  if (!raw) {
    throw new Error("No incident generated");
  }
  return { incident: toDashboardIncident(raw) };
}
