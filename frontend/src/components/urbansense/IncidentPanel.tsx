import { CheckCircle2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusTag } from "./StatusTag";
import frameAsset from "@/assets/detection-frame.jpg";
import type { Incident, IncidentStatus } from "@/lib/types";

const fmt = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

export function IncidentPanel({
  incident,
  onStatus,
}: {
  incident: Incident | null;
  onStatus: (id: string, status: IncidentStatus) => void;
}) {
  if (!incident) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        Pick a marker, a stat card or a row to see incident details here.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <StatusTag incident={incident} />
        <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
      </div>

      <div className="relative mt-3 overflow-hidden rounded-xl border border-border">
        <img
          src={frameAsset}
          alt={`Detection frame for ${incident.id}`}
          className="aspect-video w-full object-cover"
        />
        <span className="absolute top-[54%] left-[44%] h-[16%] w-[22%] rounded-md border-2 border-hazard" />
        <span className="absolute top-[46%] left-[44%] rounded bg-hazard px-1.5 py-0.5 font-mono text-[10px] text-hazard-foreground">
          Pothole {Math.round(incident.confidence * 100)}%
        </span>
      </div>

      <h3 className="mt-3 text-base font-semibold">{incident.road}</h3>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">Confidence</dt>
          <dd className="tabular-nums">{Math.round(incident.confidence * 100)}%</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Sightings</dt>
          <dd className="tabular-nums">{incident.sightings}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Coordinates</dt>
          <dd className="font-mono text-xs">
            {incident.lat.toFixed(4)}, {incident.lng.toFixed(4)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">First detected</dt>
          <dd className="text-xs">{fmt(incident.firstDetected)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Last seen</dt>
          <dd className="text-xs">{fmt(incident.lastSeen)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Frame</dt>
          <dd className="font-mono text-xs">{incident.frameLabel}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl"
          disabled={incident.status === "verified"}
          onClick={() => onStatus(incident.id, "verified")}
        >
          <ShieldCheck className="size-4" /> Mark verified
        </Button>
        <Button
          size="sm"
          className="rounded-xl"
          disabled={incident.status === "resolved"}
          onClick={() => onStatus(incident.id, "resolved")}
        >
          <CheckCircle2 className="size-4" /> Mark resolved
        </Button>
      </div>
    </div>
  );
}
