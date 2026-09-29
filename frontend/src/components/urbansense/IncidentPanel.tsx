import { CheckCircle2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import frameAsset from "@/assets/detection-frame.jpg";
import type { Incident } from "@/types/incident";

const fmtDate = (iso: string) => {
  if (!iso) return "N/A";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const fmtConf = (c: number) => {
  if (c > 1) return Math.round(c);
  return Math.round(c * 100);
};

export function IncidentPanel({
  incident,
  onStatusChange,
}: {
  incident: Incident | null;
  onStatusChange?: (id: string, status: "Verified" | "Resolved") => void;
}) {
  if (!incident) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground h-full flex items-center justify-center">
        Pick a marker, a stat card or a row to see incident details here.
      </div>
    );
  }

  const isVerified = incident.status === "Verified";
  const isResolved = incident.status === "Resolved";
  const confVal = fmtConf(incident.confidence);
  const lat = incident.latitude ?? incident.lat ?? 28.6139;
  const lng = incident.longitude ?? incident.lng ?? 77.2090;
  const areaName = incident.area ?? incident.roadSegment ?? incident.road ?? incident.id;
  const sightings = incident.sightingCount ?? incident.sightings ?? 1;
  const imageSrc = incident.representativeImage || incident.image || frameAsset;
  const firstSeenStr = fmtDate(incident.firstSeen || incident.firstDetected);
  const lastSeenStr = fmtDate(incident.lastSeen || incident.lastDetected);
  const frameNum = incident.frame || incident.frameLabel || "Frame 412";

  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              isVerified
                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                : isResolved
                ? "bg-slate-500/15 text-slate-600 dark:text-slate-400"
                : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
            }`}
          >
            {incident.status}
          </span>
          <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
        </div>

        <div className="relative mt-3 overflow-hidden rounded-xl border border-border">
          <img
            src={imageSrc}
            alt={`Detection frame for ${incident.id}`}
            className="aspect-video w-full object-cover"
          />
          <span className="absolute top-[54%] left-[44%] h-[16%] w-[22%] rounded-md border-2 border-rose-500 shadow-md" />
          <span className="absolute top-[44%] left-[44%] rounded bg-rose-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white shadow">
            Pothole {confVal}%
          </span>
        </div>

        <h3 className="mt-3 text-base font-semibold text-foreground truncate">{areaName}</h3>

        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm border-t border-border pt-3">
          <div>
            <dt className="text-xs text-muted-foreground">Confidence</dt>
            <dd className="font-semibold text-foreground">{confVal}%</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Sightings</dt>
            <dd className="font-semibold text-foreground">{sightings}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Coordinates</dt>
            <dd className="font-mono text-xs">
              {Number(lat).toFixed(4)}, {Number(lng).toFixed(4)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">First detected</dt>
            <dd className="text-xs truncate">{firstSeenStr}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Last seen</dt>
            <dd className="text-xs truncate">{lastSeenStr}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Frame</dt>
            <dd className="font-mono text-xs">{String(frameNum).startsWith("Frame") ? frameNum : `Frame ${frameNum}`}</dd>
          </div>
        </dl>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t border-border">
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl flex-1"
          disabled={isVerified}
          onClick={() => onStatusChange && onStatusChange(incident.id, "Verified")}
        >
          <ShieldCheck className="mr-1.5 size-4" /> Mark verified
        </Button>
        <Button
          size="sm"
          className="rounded-xl flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
          disabled={isResolved}
          onClick={() => onStatusChange && onStatusChange(incident.id, "Resolved")}
        >
          <CheckCircle2 className="mr-1.5 size-4" /> Mark resolved
        </Button>
      </div>
    </div>
  );
}
