import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Incident } from "@/types/incident";
import { Button } from "@/components/ui/button";
import "leaflet/dist/leaflet.css";

function MapFocus({ selected }: { selected: Incident | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (selected)
      map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), 14), {
        duration: 0.65,
      });
  }, [map, selected]);
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
        ? "#da684e"
        : incident.confidence >= 80
          ? "#dfa93c"
          : "#457e70";
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

export default function IncidentMap({
  incidents,
  selected,
  onSelect,
}: {
  incidents: Incident[];
  selected: Incident | undefined;
  onSelect: (id: string) => void;
}) {
  return (
    <MapContainer
      center={[12.9778, 77.6024]}
      zoom={13}
      scrollWheelZoom={false}
      zoomControl={false}
      className="h-full w-full"
      aria-label="Map of Bengaluru road incidents"
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
      <MapControls />
    </MapContainer>
  );
}

function MapControls() {
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
    </div>
  );
}
