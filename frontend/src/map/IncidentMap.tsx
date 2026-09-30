import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Incident } from "@/types/incident";
import { Button } from "@/components/ui/button";
import { Locate, Maximize2, RotateCcw } from "lucide-react";
import "leaflet/dist/leaflet.css";

function MapFocus({ selected }: { selected: Incident | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), 14), {
        duration: 0.65,
      });
      setTimeout(() => map.invalidateSize(), 300);
    }
  }, [map, selected]);
  return null;
}

function MapResizeObserver() {
  const map = useMap();
  useEffect(() => {
    const handleResize = () => {
      map.invalidateSize();
    };
    window.addEventListener("resize", handleResize);
    const timer = setTimeout(() => map.invalidateSize(), 400);
    return () => {
      window.removeEventListener("resize", handleResize);
      clearTimeout(timer);
    };
  }, [map]);
  return null;
}

function IncidentMarker({
  incident,
  selected,
  onSelect,
}: {
  incident: Incident;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const color =
    incident.status === "Resolved"
      ? "#80908b"
      : incident.confidence >= 90
        ? "#ef4444"
        : incident.confidence >= 80
          ? "#f59e0b"
          : "#10b981";
  return (
    <CircleMarker
      center={[incident.latitude, incident.longitude]}
      radius={selected ? 16 : 11}
      pathOptions={{
        color: "#ffffff",
        weight: selected ? 4 : 3,
        fillColor: color,
        fillOpacity: 1,
        opacity: 1,
      }}
      eventHandlers={{ click: () => onSelect(incident.id) }}
    >
      <Tooltip direction="top" offset={[0, -12]}>
        {incident.area} · {incident.confidence}% confidence
      </Tooltip>
    </CircleMarker>
  );
}

function MapControls({ onResetView }: { onResetView?: () => void }) {
  const map = useMap();
  return (
    <div className="map-zoom" onClick={(event) => event.stopPropagation()}>
      <Button
        type="button"
        variant="ghost"
        aria-label="Zoom in"
        title="Zoom in"
        onClick={() => map.zoomIn()}
      >
        +
      </Button>
      <Button
        type="button"
        variant="ghost"
        aria-label="Zoom out"
        title="Zoom out"
        onClick={() => map.zoomOut()}
      >
        −
      </Button>
      <Button
        type="button"
        variant="ghost"
        aria-label="Reset Map View"
        title="Reset Map Center"
        onClick={() => {
          map.setView([28.6139, 77.2090], 12);
          map.invalidateSize();
          if (onResetView) onResetView();
        }}
      >
        <Locate size={15} />
      </Button>
    </div>
  );
}

export default function IncidentMap({
  incidents,
  selected,
  onSelect,
}: {
  incidents: Incident[];
  selected: Incident | undefined;
  onSelect: (id: string) => void;
}) {
  const firstInc = incidents[0];
  const defaultCenter: [number, number] = selected
    ? [selected.latitude, selected.longitude]
    : firstInc
      ? [firstInc.latitude, firstInc.longitude]
      : [28.6139, 77.2090];

  return (
    <MapContainer
      center={defaultCenter}
      zoom={13}
      scrollWheelZoom={true}
      zoomControl={false}
      className="h-full w-full"
      aria-label="Map of road incidents"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {incidents.map((incident) => (
        <IncidentMarker
          key={incident.id}
          incident={incident}
          selected={incident.id === selected?.id}
          onSelect={onSelect}
        />
      ))}
      <MapFocus selected={selected} />
      <MapResizeObserver />
      <MapControls />
    </MapContainer>
  );
}
