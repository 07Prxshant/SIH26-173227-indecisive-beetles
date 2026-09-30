import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Crosshair,
  FileVideo,
  MapPin,
  Moon,
  Route,
  Search,
  ShieldCheck,
  Sun,
  UploadCloud,
} from "lucide-react";
import { ClientOnly } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiBaseUrl, toDashboardIncident, useLiveIncidents } from "@/lib/incident-api";
import type { Incident } from "@/types/incident";
import potholeEvidenceImg from "@/assets/pothole-evidence.jpg";
import { cn } from "@/lib/utils";

const IncidentMap = lazy(() => import("@/map/IncidentMap"));

type FilterKey = "all" | "verified" | "review" | "resolved" | "high";

const filters: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "verified", label: "Verified" },
  { key: "review", label: "Under review" },
  { key: "resolved", label: "Resolved" },
  { key: "high", label: "High priority" },
];

function Header({ theme, onToggleTheme }: { theme: "dark" | "light"; onToggleTheme: () => void }) {
  return (
    <header className="sticky top-0 z-[500] border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="flex size-9 items-center justify-center rounded-xl bg-foreground/90 transition-transform hover:scale-105"
          title="MIRA Home - Scroll to top"
        >
          <span className="lane-mark block h-1 w-5 rounded-full" />
        </button>
        <div className="mr-auto cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <p className="font-display text-lg leading-none font-semibold">MIRA</p>
          <p className="text-xs text-muted-foreground">Mobile Intelligence for Road Analytics</p>
        </div>
        <span className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground sm:inline-flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-2 animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
          </span>
          System operational
        </span>
        <button
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          className="inline-flex size-9 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-accent"
        >
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </button>
      </div>
    </header>
  );
}

function useCountUp(target: number) {
  const [value, setValue] = useState(0);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 700);
      setValue(Math.round(from + (target - from) * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [target]);
  return value;
}

function StatCard({
  label,
  value,
  active,
  tone,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  tone: string;
  onClick: () => void;
}) {
  const shown = useCountUp(value);
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-2xl border bg-card p-4 text-left transition-colors hover:bg-accent/40",
        active ? "border-primary shadow-sm" : "border-border",
      )}
    >
      <span className={cn("mb-2 block h-1 w-8 rounded-full", tone)} />
      <p className="font-display text-3xl font-semibold tabular-nums">{shown}</p>
      <p className="mt-1 text-xs leading-snug text-muted-foreground">{label}</p>
    </button>
  );
}

function StatCards({
  counts,
  filter,
  onFilter,
}: {
  counts: { all: number; verified: number; review: number; high: number };
  filter: FilterKey;
  onFilter: (f: FilterKey) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Incidents reported"
        value={counts.all}
        tone="bg-amber-500"
        active={filter === "all"}
        onClick={() => onFilter("all")}
      />
      <StatCard
        label="Confirmed by multiple sightings"
        value={counts.verified}
        tone="bg-emerald-500"
        active={filter === "verified"}
        onClick={() => onFilter("verified")}
      />
      <StatCard
        label="Waiting for review"
        value={counts.review}
        tone="bg-amber-400"
        active={filter === "review"}
        onClick={() => onFilter("review")}
      />
      <StatCard
        label="High priority, 90%+ confidence"
        value={counts.high}
        tone="bg-rose-500"
        active={filter === "high"}
        onClick={() => onFilter("high")}
      />
    </div>
  );
}

function IncidentPanel({
  incident,
  onStatusChange,
}: {
  incident: Incident | null;
  onStatusChange: (id: string, newStatus: "Verified" | "Resolved") => void;
}) {
  if (!incident) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        Select a marker on the map or an incident row below to view full details.
      </div>
    );
  }

  const isVerified = incident.status === "Verified";
  const isResolved = incident.status === "Resolved";

  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-semibold",
            isVerified && "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
            isResolved && "bg-slate-500/15 text-slate-600 dark:text-slate-400",
            !isVerified && !isResolved && "bg-amber-500/15 text-amber-600 dark:text-amber-400",
          )}
        >
          {incident.status}
        </span>
        <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
      </div>

      <div className="relative mt-3 overflow-hidden rounded-xl border border-border">
        <img
          src={incident.representativeImage || potholeEvidenceImg}
          alt={`Detection frame for ${incident.id}`}
          className="aspect-video w-full object-cover"
        />
        <span className="absolute top-[54%] left-[44%] h-[16%] w-[22%] rounded-md border-2 border-rose-500 shadow-md" />
        <span className="absolute top-[44%] left-[44%] rounded bg-rose-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white shadow">
          Pothole {incident.confidence}%
        </span>
      </div>

      <h3 className="mt-3 text-base font-semibold text-foreground">{incident.area}</h3>
      {incident.roadSegment && (
        <p className="text-xs text-muted-foreground">{incident.roadSegment}</p>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm border-t border-border pt-3">
        <div>
          <dt className="text-xs text-muted-foreground">Confidence</dt>
          <dd className="font-semibold text-foreground">{incident.confidence}%</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Sightings</dt>
          <dd className="font-semibold text-foreground">{incident.sightingCount}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Coordinates</dt>
          <dd className="font-mono text-xs">
            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">First detected</dt>
          <dd className="text-xs">{incident.firstSeen}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Last seen</dt>
          <dd className="text-xs">{incident.lastSeen}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Frame</dt>
          <dd className="font-mono text-xs">Frame {incident.frame || 412}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t border-border">
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl flex-1"
          disabled={isVerified}
          onClick={() => onStatusChange(incident.id, "Verified")}
        >
          <ShieldCheck className="mr-1.5 size-4" /> Mark verified
        </Button>
        <Button
          size="sm"
          className="rounded-xl flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
          disabled={isResolved}
          onClick={() => onStatusChange(incident.id, "Resolved")}
        >
          <CheckCircle2 className="mr-1.5 size-4" /> Mark resolved
        </Button>
      </div>
    </div>
  );
}

function UploadLab({ onVideoProcessed }: { onVideoProcessed: (incidents: Incident[]) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);
  const [locationText, setLocationText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [stats, setStats] = useState<{
    total_frames: number;
    potholes_detected: number;
    events_generated: number;
    severity_breakdown: { High: number; Medium: number; Low: number };
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const requestDeviceLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    setLocationText("Fetching current location...");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocationText(`${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
      },
      (err) => {
        console.warn("High accuracy geolocation timeout, falling back to standard accuracy:", err);
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            setLocationText(`${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
          },
          () => {
            setLocationText("28.6139, 77.2090");
          },
          { enableHighAccuracy: false, timeout: 8000 }
        );
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  };

  const handleProcess = async () => {
    if (!file) {
      alert("Please select a road video file first.");
      return;
    }
    setIsProcessing(true);
    setProgressMsg("Uploading road video to YOLOv8 inference worker...");

    try {
      const formData = new FormData();
      formData.append("video", file);
      formData.append("file", file);
      if (locationText.trim()) {
        formData.append("user_location", locationText.trim());
        const coords = locationText.split(",").map((s) => parseFloat(s.trim()));
        const latVal = coords[0];
        const lngVal = coords[1];
        if (coords.length === 2 && latVal !== undefined && lngVal !== undefined && !isNaN(latVal) && !isNaN(lngVal)) {
          formData.append("latitude", latVal.toString());
          formData.append("longitude", lngVal.toString());
        }
      }
      if (gpsFile) {
        formData.append("gps", gpsFile);
      }

      const uploadUrl = apiBaseUrl.endsWith("/api/v1") ? `${apiBaseUrl}/videos/upload` : `${apiBaseUrl}/api/v1/videos/upload`;
      const res = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed with status ${res.status}`);
      }

      const data = await res.json();
      const rawIncidents = data.fused_incidents || data.incidents || [];
      const dashIncidents = rawIncidents.map(toDashboardIncident);

      setStats({
        total_frames: data.total_frames || 0,
        potholes_detected: data.potholes_detected || 0,
        events_generated: data.events_generated || 0,
        severity_breakdown: data.severity_breakdown || { High: 0, Medium: 0, Low: 0 },
      });

      onVideoProcessed(dashIncidents);
      setProgressMsg(`Analysis complete! Processed ${dashIncidents.length} incidents.`);
    } catch (err) {
      console.error("Video processing error:", err);
      alert("Video processing failed. Please check backend connection.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <section className="grid gap-4 rounded-2xl border border-border bg-card p-4 sm:p-6 lg:grid-cols-2 shadow-sm">
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
            "mt-4 rounded-2xl border-2 border-dashed p-6 text-center transition-colors cursor-pointer",
            dragOver ? "border-primary bg-accent/50" : "border-border hover:border-primary/50",
          )}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">
            {file ? file.name : "Drop a video here, or choose a file"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">MP4, AVI, MOV or WEBM</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.avi,.mov,.webm"
            className="sr-only"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-3 rounded-xl pointer-events-none"
          >
            <FileVideo className="mr-1.5 size-4" /> Choose file
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
                value={locationText}
                onChange={(e) => setLocationText(e.target.value)}
                placeholder="Enter city, road or coordinates"
                className="rounded-xl pl-9"
              />
            </div>
            <Button type="button" variant="outline" className="rounded-xl" onClick={requestDeviceLocation}>
              <Crosshair className="mr-1.5 size-4" /> Use my location
            </Button>
          </div>
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent/40">
          <Route className="size-4" />
          <span className="truncate">{gpsFile ? gpsFile.name : "Add a GPS track (optional)"}</span>
          <input
            type="file"
            accept=".gpx,.csv,.json"
            className="sr-only"
            onChange={(e) => setGpsFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <Button
          type="button"
          className="mt-4 w-full rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
          onClick={handleProcess}
          disabled={isProcessing}
        >
          {isProcessing ? progressMsg || "Processing video..." : "Process video"}
        </Button>
      </div>

      <div>
        <div className="relative aspect-video overflow-hidden rounded-2xl border border-border bg-slate-900 flex items-center justify-center">
          <img
            src={potholeEvidenceImg}
            alt="Sample preview"
            className="w-full h-full object-cover opacity-80"
          />
          {isProcessing && <div className="scan-line absolute inset-x-0 top-0 h-6" />}
          <div className="absolute top-[45%] left-[38%] h-[26%] w-[26%] rounded-md border-2 border-rose-500">
            <span className="absolute -top-6 left-0 rounded bg-rose-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white shadow">
              Pothole 96%
            </span>
          </div>
          <span className="absolute bottom-3 left-3 font-mono text-[10px] text-white/70 bg-black/60 px-2 py-0.5 rounded backdrop-blur">
            YOLOv8n + ByteTrack · 30 FPS
          </span>
        </div>

        {stats && (
          <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs space-y-3 animate-in fade-in duration-300">
            <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
              <span className="font-bold text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-500 animate-ping inline-block" />
                Video Analysis Results
              </span>
              <span className="text-[11px] text-muted-foreground font-mono">{stats.total_frames} Frames Scanned</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-card p-2.5 border border-border">
                <span className="block text-lg font-extrabold text-foreground tabular-nums">{stats.potholes_detected}</span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Pothole Sightings</span>
              </div>
              <div className="rounded-lg bg-card p-2.5 border border-border">
                <span className="block text-lg font-extrabold text-foreground tabular-nums">{stats.total_frames}</span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Frames Scanned</span>
              </div>
              <div className="rounded-lg bg-card p-2.5 border border-border">
                <span className="block text-lg font-extrabold text-foreground tabular-nums">{stats.events_generated}</span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Geotagged Events</span>
              </div>
            </div>

            <div className="pt-1">
              <span className="block text-[11px] font-semibold text-muted-foreground mb-1.5">Detection Severity Breakdown:</span>
              <div className="flex items-center gap-2">
                <span className="flex-1 rounded-md bg-rose-500/15 text-rose-600 dark:text-rose-400 px-2 py-1 text-center font-semibold text-[11px] border border-rose-500/20">
                  High: {stats.severity_breakdown.High}
                </span>
                <span className="flex-1 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 px-2 py-1 text-center font-semibold text-[11px] border border-amber-500/20">
                  Medium: {stats.severity_breakdown.Medium}
                </span>
                <span className="flex-1 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 px-2 py-1 text-center font-semibold text-[11px] border border-emerald-500/20">
                  Low: {stats.severity_breakdown.Low}
                </span>
              </div>
            </div>
          </div>
        )}

        {!stats && (
          <div className="mt-4 rounded-xl border border-border bg-card p-4 text-xs space-y-2">
            <h4 className="font-semibold text-sm">Processing Pipeline</h4>
            <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
              <div className="rounded bg-accent/60 p-2">
                <span className="block font-bold">1. Footage</span>
                <span className="text-muted-foreground">Video Intake</span>
              </div>
              <div className="rounded bg-accent/60 p-2">
                <span className="block font-bold">2. Detection</span>
                <span className="text-muted-foreground">YOLOv8 Inference</span>
              </div>
              <div className="rounded bg-accent/60 p-2">
                <span className="block font-bold">3. Fusion</span>
                <span className="text-muted-foreground">Kafka Stream</span>
              </div>
              <div className="rounded bg-accent/60 p-2">
                <span className="block font-bold">4. Review</span>
                <span className="text-muted-foreground">Geotagged Log</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
export default function Dashboard() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const { incidents: initialIncidents, loading, error, addIncidents } = useLiveIncidents();
  const [incidentsList, setIncidentsList] = useState<Incident[]>([]);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<"id" | "area" | "confidence" | "sightingCount" | "status" | "lastSeen">("lastSeen");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  useEffect(() => {
    if (initialIncidents && initialIncidents.length > 0) {
      setIncidentsList(initialIncidents);
      if (!selectedId && initialIncidents[0]) setSelectedId(initialIncidents[0].id);
    }
  }, [initialIncidents]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const visibleIncidents = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return incidentsList
      .filter((i) => {
        const matchesQuery = !q || i.id.toLowerCase().includes(q) || i.area.toLowerCase().includes(q) || i.roadSegment.toLowerCase().includes(q);
        if (!matchesQuery) return false;
        if (filter === "all") return true;
        if (filter === "verified") return i.status === "Verified";
        if (filter === "review") return i.status === "Under review";
        if (filter === "resolved") return i.status === "Resolved";
        if (filter === "high") return i.confidence >= 90 && i.status !== "Resolved";
        return true;
      })
      .sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (typeof av === "number" && typeof bv === "number") return (av - bv) * sortDir;
        return String(av).localeCompare(String(bv)) * sortDir;
      });
  }, [incidentsList, filter, searchQuery, sortKey, sortDir]);

  const counts = useMemo(
    () => ({
      all: incidentsList.length,
      verified: incidentsList.filter((i) => i.status === "Verified").length,
      review: incidentsList.filter((i) => i.status === "Under review").length,
      high: incidentsList.filter((i) => i.confidence >= 90 && i.status !== "Resolved").length,
    }),
    [incidentsList],
  );

  const selectedIncident = useMemo(
    () => incidentsList.find((i) => i.id === selectedId) || visibleIncidents[0] || null,
    [incidentsList, selectedId, visibleIncidents],
  );

  const handleStatusChange = (id: string, newStatus: "Verified" | "Resolved") => {
    setIncidentsList((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: newStatus } : item))
    );
  };

  const handleVideoProcessed = (newIncidents: Incident[]) => {
    if (newIncidents.length > 0 && newIncidents[0]) {
      addIncidents(newIncidents);
      setIncidentsList((prev) => [...newIncidents, ...prev]);
      setSelectedId(newIncidents[0].id);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200">
      <Header theme={theme} onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")} />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <section className="grid gap-4 lg:grid-cols-[1.6fr_1fr] items-stretch">
          <div className="relative min-h-[480px] h-[520px] lg:h-full overflow-hidden rounded-3xl border border-border shadow-sm">
            <ClientOnly fallback={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading GIS Map...</div>}>
              <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading GIS Map...</div>}>
                <IncidentMap
                  incidents={visibleIncidents}
                  selected={selectedIncident || undefined}
                  onSelect={(id) => setSelectedId(id)}
                />
              </Suspense>
            </ClientOnly>

            {/* Floating Top-Left Header Banner */}
            <div className="pointer-events-none absolute top-4 left-4 z-[400] max-w-md rounded-2xl bg-background/90 p-4 shadow-lg backdrop-blur sm:top-6 sm:left-6 sm:p-5 border border-border">
              <h1 className="text-2xl leading-tight font-semibold sm:text-3xl text-foreground">
                Every pothole, on the map.
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-muted-foreground">
                Footage in, geotagged incidents out — so crews fix the worst roads first.
              </p>
            </div>

            {/* Floating Bottom-Left Filter Pills */}
            <div className="absolute bottom-4 left-4 z-[400] flex flex-wrap gap-2 pr-4">
              {filters.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium backdrop-blur transition-all shadow-sm",
                    filter === f.key
                      ? "border-primary bg-primary text-primary-foreground font-semibold"
                      : "border-border bg-card/90 text-foreground hover:bg-accent",
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <StatCards counts={counts} filter={filter} onFilter={(f) => setFilter(f)} />
            <div className="flex-1">
              <IncidentPanel incident={selectedIncident} onStatusChange={handleStatusChange} />
            </div>
          </div>
        </section>

        <UploadLab onVideoProcessed={handleVideoProcessed} />

        {/* Incident Table */}
        <section className="rounded-2xl border border-border bg-card p-4 sm:p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="mr-auto text-xl font-semibold">Incident log</h2>
            <div className="relative w-full sm:w-72">
              <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID or area"
                className="rounded-xl pl-9"
              />
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  {[
                    { key: "id", label: "ID" },
                    { key: "area", label: "Road / Area" },
                    { key: "confidence", label: "Confidence" },
                    { key: "sightingCount", label: "Sightings" },
                    { key: "status", label: "Status" },
                    { key: "lastSeen", label: "Last seen" },
                  ].map((col) => (
                    <th key={col.key} className="py-2 pr-4 font-medium">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-foreground"
                        onClick={() => {
                          const k = col.key as typeof sortKey;
                          if (sortKey === k) setSortDir(sortDir === 1 ? -1 : 1);
                          else {
                            setSortKey(k);
                            setSortDir(1);
                          }
                        }}
                      >
                        {col.label}
                        {sortKey === col.key && (sortDir === 1 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleIncidents.map((inc) => (
                  <tr
                    key={inc.id}
                    onClick={() => setSelectedId(inc.id)}
                    className={cn(
                      "cursor-pointer border-b border-border/60 transition-colors hover:bg-accent/40",
                      selectedId === inc.id && "bg-accent/60 font-medium",
                    )}
                  >
                    <td className="py-3 pr-4 font-mono text-xs text-primary">{inc.id}</td>
                    <td className="py-3 pr-4">{inc.area}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
                          <span
                            className="block h-1.5 rounded-full bg-emerald-500"
                            style={{ width: `${inc.confidence}%` }}
                          />
                        </span>
                        <span className="tabular-nums text-xs">{inc.confidence}%</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 tabular-nums text-xs">{inc.sightingCount}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={cn(
                          "inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold",
                          inc.status === "Verified" && "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
                          inc.status === "Resolved" && "bg-slate-500/15 text-slate-600 dark:text-slate-400",
                          inc.status !== "Verified" && inc.status !== "Resolved" && "bg-amber-500/15 text-amber-600 dark:text-amber-400",
                        )}
                      >
                        {inc.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-xs text-muted-foreground">{inc.lastSeen}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibleIncidents.length === 0 && (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No matching incidents found.
              </p>
            )}
          </div>
        </section>

        <footer className="pb-6 text-xs text-muted-foreground flex justify-between items-center border-t border-border pt-4">
          <span>MIRA (Mobile Intelligence for Road Analytics) Portal</span>
          <span>Smart India Hackathon 2026</span>
        </footer>
      </main>
    </div>
  );
}
