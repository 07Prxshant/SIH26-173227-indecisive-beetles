import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Incident } from "@/types/incident";
import "leaflet/dist/leaflet.css";

function MapFocus({ selected }: { selected: Incident | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      const lat = selected.latitude ?? selected.lat ?? 28.6139;
      const lng = selected.longitude ?? selected.lng ?? 77.2090;
      map.flyTo([lat, lng], 15, { duration: 0.8 });
    }
  }, [map, selected]);
  return null;
}

export function IncidentMap({
  incidents,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const first = incidents[0];
  const centerLat = first ? (first.latitude ?? first.lat ?? 28.6139) : 28.6139;
  const centerLng = first ? (first.longitude ?? first.lng ?? 77.2090) : 77.2090;

  return (
    <MapContainer
      center={[centerLat, centerLng]}
      zoom={13}
      zoomControl={false}
      className="h-full w-full"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {incidents.map((i) => {
        const lat = i.latitude ?? i.lat ?? 28.6139;
        const lng = i.longitude ?? i.lng ?? 77.2090;
        const isSelected = i.id === selectedId;
        const color =
          i.status === "Resolved" || i.status === "resolved"
            ? "#80908b"
            : i.confidence >= 90
            ? "#ef4444"
            : i.confidence >= 80
            ? "#f59e0b"
            : "#10b981";

        return (
          <CircleMarker
            key={i.id}
            center={[lat, lng]}
            radius={isSelected ? 14 : 9}
            pathOptions={{
              color: "#ffffff",
              weight: isSelected ? 3 : 2,
              fillColor: color,
              fillOpacity: 1,
            }}
            eventHandlers={{ click: () => onSelect(i.id) }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {i.area || i.roadSegment || i.id} · {i.confidence}%
            </Tooltip>
          </CircleMarker>
        );
      })}
      <MapFocus selected={incidents.find((i) => i.id === selectedId)} />
    </MapContainer>
  );
}

export default IncidentMap;
