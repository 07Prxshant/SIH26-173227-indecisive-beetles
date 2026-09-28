import { useEffect, useRef, useState } from "react";
import { Crosshair, FileVideo, MapPin, Route, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { searchLocations, uploadVideo } from "@/lib/api";
import { PipelineStrip } from "./PipelineStrip";
import type { Incident } from "@/lib/types";

const ACCEPT = ".mp4,.avi,.mov,.webm,video/*";

export function UploadLab({ onProcessed }: { onProcessed: (incident: Incident) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [gps, setGps] = useState<File | null>(null);
  const [location, setLocation] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [step, setStep] = useState(0);
  const [running, setRunning] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let alive = true;
    searchLocations(location).then((s) => alive && setSuggestions(s));
    return () => {
      alive = false;
    };
  }, [location]);

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setLocation(`${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`),
      () => toast.error("Could not read your location."),
    );
  };

  const process = async () => {
    if (!file) {
      toast.error("Add a road video first.");
      return;
    }
    setRunning(true);
    for (let s = 1; s <= 3; s++) {
      setStep(s);
      await new Promise((r) => setTimeout(r, 700));
    }
    const { incident } = await uploadVideo(file, location, gps);
    setStep(4);
    setRunning(false);
    onProcessed(incident);
    toast.success(`${incident.id} placed on the map.`);
  };

  return (
    <section className="grid gap-4 rounded-2xl border border-border bg-card p-4 sm:p-6 lg:grid-cols-2">
      <div>
        <h2 className="text-xl font-semibold">Analyse road footage</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a dashcam clip. Detections are geotagged and added to the log.
        </p>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f) setFile(f);
          }}
          className={cn(
            "mt-4 rounded-2xl border-2 border-dashed p-6 text-center transition-colors",
            dragOver ? "border-primary bg-accent/50" : "border-border",
          )}
        >
          <UploadCloud className="mx-auto size-6 text-muted-foreground" />
          <p className="mt-2 text-sm">
            {file ? file.name : "Drop a video here, or choose a file"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">MP4, AVI, MOV or WEBM</p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Button
            variant="outline"
            size="sm"
            className="mt-3 rounded-xl"
            onClick={() => inputRef.current?.click()}
          >
            <FileVideo className="size-4" /> Choose file
          </Button>
        </div>

        <div className="mt-4 space-y-2">
          <label htmlFor="location" className="text-sm font-medium">
            Location
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <MapPin className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Road or junction"
                autoComplete="off"
                className="rounded-xl pl-9"
              />
              {suggestions.length > 0 && suggestions[0] !== location && (
                <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-border bg-popover shadow-lg">
                  {suggestions.map((s) => (
                    <li key={s}>
                      <button
                        className="w-full px-3 py-2 text-left text-sm hover:bg-accent"
                        onClick={() => setLocation(s)}
                      >
                        {s}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <Button variant="outline" className="rounded-xl" onClick={useMyLocation}>
              <Crosshair className="size-4" /> Use my location
            </Button>
          </div>
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent/40">
          <Route className="size-4" />
          {gps ? gps.name : "Add a GPS track (optional)"}
          <input
            type="file"
            accept=".gpx,.csv,.json"
            className="sr-only"
            onChange={(e) => setGps(e.target.files?.[0] ?? null)}
          />
        </label>

        <Button className="mt-4 w-full rounded-xl" onClick={process} disabled={running}>
          {running ? "Processing…" : "Process video"}
        </Button>
      </div>

      <div>
        <div className="relative aspect-video overflow-hidden rounded-2xl border border-border bg-muted">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_60%,color-mix(in_oklab,var(--color-foreground)_12%,transparent),transparent_70%)]" />
          {running && <div className="scan-line absolute inset-x-0 top-0 h-6" />}
          <div className="absolute top-[45%] left-[38%] h-[26%] w-[26%] rounded-md border-2 border-hazard">
            <span className="absolute -top-6 left-0 rounded bg-hazard px-1.5 py-0.5 font-mono text-[10px] whitespace-nowrap text-hazard-foreground">
              Pothole 96%
            </span>
          </div>
          <span className="absolute bottom-3 left-3 font-mono text-[10px] text-muted-foreground">
            yolov8n · 30 fps
          </span>
        </div>
        <div className="mt-4">
          <PipelineStrip step={step} />
        </div>
      </div>
    </section>
  );
}
