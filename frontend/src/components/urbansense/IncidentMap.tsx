import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { isHighPriority, type Incident } from "@/lib/types";

function markerClass(i: Incident, selected: boolean, isNew: boolean) {
  const tone = isHighPriority(i)
    ? "us-marker--hazard"
    : i.status === "verified"
      ? "us-marker--verified"
      : i.status === "review"
        ? "us-marker--review"
        : "us-marker--resolved";
  return ["us-marker", tone, selected ? "us-marker--selected" : "", isNew ? "us-marker--new" : ""]
    .filter(Boolean)
    .join(" ");
}

function FlyTo({ incident }: { incident: Incident | null }) {
  const map = useMap();
  useEffect(() => {
    if (incident) map.flyTo([incident.lat, incident.lng], 15, { duration: 0.8 });
  }, [incident, map]);
  return null;
}

export default function IncidentMap({
  incidents,
  selectedId,
  newId,
  onSelect,
}: {
  incidents: Incident[];
  selectedId: string | null;
  newId: string | null;
  onSelect: (id: string) => void;
}) {
  const selected = useMemo(
    () => incidents.find((i) => i.id === selectedId) ?? null,
    [incidents, selectedId],
  );

  return (
    <MapContainer
      center={[12.9716, 77.5946]}
      zoom={13}
      scrollWheelZoom
      className="h-full w-full"
      zoomControl={false}
      attributionControl={false}
    >
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FlyTo incident={selected} />
      {incidents.map((i) => (
        <Marker
          key={i.id}
          position={[i.lat, i.lng]}
          keyboard
          alt={`${i.id} on ${i.road}`}
          title={`${i.id} — ${i.road}`}
          icon={L.divIcon({
            className: "",
            html: `<span class="${markerClass(i, i.id === selectedId, i.id === newId)}" role="img" aria-label="${i.id}"></span>`,
            iconSize: [18, 18],
            iconAnchor: [9, 9],
          })}
          eventHandlers={{ click: () => onSelect(i.id), keypress: () => onSelect(i.id) }}
        />
      ))}
    </MapContainer>
  );
}
