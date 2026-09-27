import { lazy, Suspense, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Crosshair,
  Eye,
  Filter,
  MapPin,
  Radio,
  Search,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import { ClientOnly } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { apiBaseUrl, useLiveIncidents } from "@/lib/incident-api";
import type { Incident } from "@/types/incident";

const IncidentMap = lazy(() => import("@/map/IncidentMap"));
type FilterValue = "All incidents" | "Verified" | "Under review" | "Resolved";

function ConfidenceBadge({ value }: { value: number }) {
  return (
    <span
      className={`confidence ${value >= 90 ? "confidence-high" : value >= 80 ? "confidence-medium" : "confidence-low"}`}
    >
      <span className="confidence-dot" />
      {value}% confidence
    </span>
  );
}

function VideoUploadCard({ onVideoProcessed }: { onVideoProcessed?: (incidents: any[]) => void }) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "completed" | "failed">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const handleProcessVideo = async () => {
    if (!selectedFile) return;
    setStatus("uploading");
    setMessage(`Uploading ${selectedFile.name}...`);

    const formData = new FormData();
    formData.append("video", selectedFile);
    if (gpsFile) {
      formData.append("gps", gpsFile);
    }

    try {
      setStatus("processing");
      setMessage("Processing video: running YOLOv8 detection & ByteTrack tracking...");
      const response = await fetch(`${apiBaseUrl}/videos/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Video processing failed.");
      }

      const data = await response.json();
      setStatus("completed");
      setMessage(data.message || "Video processing completed successfully!");

      if (onVideoProcessed && data.incidents) {
        onVideoProcessed(data.incidents);
      }
    } catch (err: any) {
      setStatus("failed");
      setMessage(err.message || "An error occurred during video upload and processing.");
    }
  };

  return (
    <div className="metric metric-upload" style={{ gridColumn: "span 12", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "12px", padding: "18px 22px", marginBottom: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Upload size={20} style={{ color: "#38bdf8" }} />
          <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, color: "#f8fafc" }}>Upload Road Video for YOLOv8 Pothole Detection</h3>
        </div>
        <span className="eyebrow" style={{ color: "#94a3b8" }}>SIH 2026 REAL WORKFLOW</span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 260px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "6px" }}>Select Road Video (.mp4)</label>
          <input
            type="file"
            accept="video/*,.mp4,.avi,.mov,.mkv"
            onChange={(e) => {
              setSelectedFile(e.target.files?.[0] ?? null);
              setStatus("idle");
              setMessage(null);
            }}
            style={{ fontSize: "0.85rem", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "6px", padding: "8px 12px", width: "100%", color: "#e2e8f0" }}
          />
        </div>

        <div style={{ flex: "1 1 220px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "6px" }}>GPS Trace Data (Optional .csv)</label>
          <input
            type="file"
            accept=".csv,.gpx"
            onChange={(e) => setGpsFile(e.target.files?.[0] ?? null)}
            style={{ fontSize: "0.85rem", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "6px", padding: "8px 12px", width: "100%", color: "#e2e8f0" }}
          />
        </div>

        <div>
          <Button
            onClick={handleProcessVideo}
            disabled={!selectedFile || status === "uploading" || status === "processing"}
            style={{ background: selectedFile ? "#0284c7" : "rgba(255,255,255,0.1)", color: "#fff", fontWeight: 600, padding: "10px 24px", cursor: selectedFile ? "pointer" : "not-allowed" }}
          >
            {status === "uploading" || status === "processing" ? "Processing Video..." : "Process Video"}
          </Button>
        </div>
      </div>

      {message && (
        <div style={{ marginTop: "14px", padding: "10px 14px", borderRadius: "6px", fontSize: "0.88rem", background: status === "completed" ? "rgba(16, 185, 129, 0.15)" : status === "failed" ? "rgba(239, 68, 68, 0.15)" : "rgba(56, 189, 248, 0.15)", border: `1px solid ${status === "completed" ? "#10b981" : status === "failed" ? "#ef4444" : "#38bdf8"}`, color: "#f8fafc" }}>
          <strong>Status: {status.toUpperCase()}</strong> — {message}
        </div>
      )}
    </div>
  );
}

function IncidentPanel({
  incident,
  onClose,
}: {
  incident: Incident | undefined;
  onClose: () => void;
}) {
  if (!incident)
    return (
      <div className="detail-empty">
        <Crosshair size={24} />
        <h3>Select an incident</h3>
        <p>Choose a map marker or an incident from the list to inspect its details.</p>
      </div>
    );
  return (
    <div className="detail-content" key={incident.id}>
      <div className="detail-topline">
        <span className="eyebrow">INCIDENT DETAILS</span>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Close incident details"
          title="Close details"
          onClick={onClose}
        >
          <X size={17} />
        </Button>
      </div>
      <div className="detail-title-row">
        <div>
          <div className="detail-id">{incident.id}</div>
          <h2>{incident.area}</h2>
          <p>{incident.roadSegment}</p>
        </div>
        <span
          className={`status-pill ${incident.status === "Verified" ? "status-verified" : incident.status === "Resolved" ? "status-resolved" : "status-review"}`}
        >
          {incident.status === "Verified" && <Check size={12} />}
          {incident.status}
        </span>
      </div>
      {incident.image ? (
        <div className="evidence-image">
          <img
            src={incident.image}
            alt="YOLOv8 pothole detection evidence frame"
            loading="lazy"
            width={1024}
            height={768}
          />
          <span>YOLOv8 DETECTION FRAME</span>
        </div>
      ) : (
        <div className="no-evidence">
          <Eye size={18} /> No reference image available
        </div>
      )}
      <div className="detail-confidence">
        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "8px" }}>
          <div>
            <span className="eyebrow">YOLO DETECTOR CONFIDENCE</span>
            <strong style={{ fontSize: "1.1rem", display: "block" }}>
              {incident.detectorConfidence ?? incident.confidence}%
            </strong>
          </div>
          <div>
            <span className="eyebrow">FINAL INCIDENT CONFIDENCE</span>
            <strong style={{ fontSize: "1.1rem", display: "block", color: "#38bdf8" }}>
              {incident.confidence}%
            </strong>
          </div>
        </div>
        <div className="confidence-track">
          <span style={{ width: `${incident.confidence}%` }} />
        </div>
        <p style={{ marginTop: "8px" }}>
          Based on {incident.sightingCount} matched{" "}
          {incident.sightingCount === 1 ? "sighting" : "sightings"} (ByteTrack ID: {incident.trackId ?? "N/A"})
        </p>
      </div>
      <div className="detail-fields">
        <div>
          <span>Severity</span>
          <strong>
            <span className={`severity-dot severity-${incident.severity.toLowerCase()}`} />
            {incident.severity}
          </strong>
        </div>
        <div>
          <span>ByteTrack ID</span>
          <strong>{incident.trackId ?? "N/A"}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{incident.sourceId ?? "Road Video"}</strong>
        </div>
        <div>
          <span>Sightings</span>
          <strong>{incident.sightingCount} detections</strong>
        </div>
        <div>
          <span>First seen</span>
          <strong>{incident.firstSeen}</strong>
        </div>
        <div>
          <span>Last seen</span>
          <strong>{incident.lastSeen}</strong>
        </div>
        <div>
          <span>Coordinates</span>
          <strong>
            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </strong>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const incidents = useLiveIncidents();
  const [selectedId, setSelectedId] = useState<string | null>(() => incidents[0]?.id ?? null);
  const [filter, setFilter] = useState<FilterValue>("All incidents");
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const selected = incidents.find((item) => item.id === selectedId);
  const filtered = useMemo(
    () =>
      incidents.filter(
        (item) =>
          (filter === "All incidents" || item.status === filter) &&
          `${item.id} ${item.area} ${item.roadSegment}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [filter, incidents, query],
  );
  const verified = incidents.filter((item) => item.status === "Verified").length;
  const highConfidence = incidents.filter(
    (item) => item.confidence >= 90 && item.status !== "Resolved",
  ).length;

  return (
    <div className="dashboard">
      <header className="site-header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-mark">
              <span />
              <span />
              <span />
              <span />
            </span>
            <span>
              Urban<span>Sense</span>
            </span>
          </div>
          <div className="header-center">
            <span className="header-divider" />
            ROAD INTELLIGENCE PLATFORM <span className="header-divider" />
          </div>
          <div className="header-right">
            <span className="demo-badge">LIVE DEMO</span>
            <span className="header-location">
              <MapPin size={14} /> Bengaluru, IN
            </span>
            <span className="header-avatar">US</span>
          </div>
        </div>
      </header>
      <main className="main-wrap">
        <div className="page-intro">
          <div>
            <div className="intro-label">
              <span className="live-pulse" /> CITY OVERVIEW <span className="intro-slash">/</span>{" "}
              BENGALURU
            </div>
            <h1>
              Road incident overview<span className="title-period">.</span>
            </h1>
            <p>Detection intelligence across your city streets.</p>
          </div>
          <div className="snapshot">
            <Clock3 size={15} />
            <span>Snapshot · 27 Sep 2026</span>
            <span className="snapshot-separator" /> <span>UrbanSense ML Engine</span>
          </div>
        </div>
        <div className="metrics">
          <div className="metric">
            <div className="metric-heading">
              <span>Total incidents</span>
              <MapPin size={17} />
            </div>
            <div className="metric-value">
              {incidents.length.toString().padStart(2, "0")}
              <span className="metric-context">
                <ArrowUpRight size={14} /> Tracked on map
              </span>
            </div>
            <div className="metric-foot">Verified road pothole incidents</div>
          </div>
          <div className="metric">
            <div className="metric-heading">
              <span>Verified potholes</span>
              <ShieldCheck size={18} />
            </div>
            <div className="metric-value">
              {verified.toString().padStart(2, "0")}
              <span className="metric-context">
                <Check size={14} /> Fused & verified
              </span>
            </div>
            <div className="metric-foot">Meeting verification threshold</div>
          </div>
          <div className="metric">
            <div className="metric-heading">
              <span>High confidence</span>
              <Activity size={18} />
            </div>
            <div className="metric-value">
              {highConfidence.toString().padStart(2, "0")}
              <span className="metric-context metric-context-orange">
                <ArrowUpRight size={14} /> 90% or above
              </span>
            </div>
            <div className="metric-foot">Active incidents with strong signals</div>
          </div>
          <div className="metric metric-process">
            <div className="metric-heading">
              <span>Detection pipeline</span>
              <Radio size={18} />
            </div>
            <div className="pipeline">
              <span>Video</span>
              <ChevronRight size={14} />
              <span>Detect</span>
              <ChevronRight size={14} />
              <span>Verify</span>
              <ChevronRight size={14} />
              <span className="pipeline-final">Map</span>
            </div>
            <div className="metric-foot">From street footage to actionable insight</div>
          </div>
        </div>

        <VideoUploadCard
          onVideoProcessed={(newIncidents) => {
            if (newIncidents && newIncidents.length > 0) {
              setSelectedId(newIncidents[0].id);
            }
          }}
        />

        <div className="workspace-heading">
          <div>
            <span className="eyebrow">SPATIAL VIEW</span>
            <h2>
              Incident map <span className="heading-count">{filtered.length}</span>
            </h2>
          </div>
          <div className="map-key">
            <span>
              <i className="key-dot key-high" /> High confidence
            </span>
            <span>
              <i className="key-dot key-medium" /> Medium
            </span>
            <span>
              <i className="key-dot key-low" /> Lower / resolved
            </span>
          </div>
        </div>
        <div className="workspace">
          <section className="map-panel" aria-label="Incident map">
            <div className="map-toolbar">
              <div className="map-region">
                <Crosshair size={15} /> Central Bengaluru <ChevronDown size={14} />
              </div>
              <span className="map-toolbar-count">{filtered.length} locations shown</span>
            </div>
            <div className="map-canvas">
              <ClientOnly fallback={<div className="map-placeholder">Loading map…</div>}>
                <Suspense fallback={<div className="map-placeholder">Loading map…</div>}>
                  <IncidentMap incidents={filtered} selected={selected} onSelect={setSelectedId} />
                </Suspense>
              </ClientOnly>
            </div>
            <div className="map-bottom">
              <span>
                <span className="map-bottom-indicator" /> OpenStreetMap basemap
              </span>
              <span>
                Scroll to browse incidents below <ArrowDownRight size={13} />
              </span>
            </div>
          </section>
          <aside className="detail-panel" aria-label="Incident details">
            <IncidentPanel incident={selected} onClose={() => setSelectedId(null)} />
          </aside>
        </div>
        <section className="incidents-section">
          <div className="incidents-header">
            <div>
              <span className="eyebrow">INCIDENT LOG</span>
              <h2>
                Recent detections <span className="heading-count">{filtered.length}</span>
              </h2>
            </div>
            <div className="list-tools">
              <label className="search-field">
                <Search size={16} />
                <input
                  aria-label="Search incidents"
                  placeholder="Search incidents..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <div className="filter-wrap">
                <Button
                  variant="outline"
                  onClick={() => setShowFilters(!showFilters)}
                  aria-expanded={showFilters}
                >
                  <SlidersHorizontal size={15} /> {filter === "All incidents" ? "Filter" : filter}{" "}
                  <ChevronDown size={14} />
                </Button>
                {showFilters && (
                  <div className="filter-menu">
                    {(
                      ["All incidents", "Verified", "Under review", "Resolved"] as FilterValue[]
                    ).map((option) => (
                      <Button
                        key={option}
                        variant="ghost"
                        onClick={() => {
                          setFilter(option);
                          setShowFilters(false);
                        }}
                      >
                        <span>{option}</span>
                        {filter === option && <Check size={14} />}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="incident-list">
            <div className="list-columns">
              <span>INCIDENT / LOCATION</span>
              <span>CONFIDENCE</span>
              <span>SIGHTINGS</span>
              <span>STATUS</span>
              <span>LAST SEEN</span>
              <span />
            </div>
            {filtered.length ? (
              filtered.map((incident) => (
                <Button
                  key={incident.id}
                  variant="ghost"
                  className={`incident-row ${selectedId === incident.id ? "incident-row-active" : ""}`}
                  onClick={() => {
                    setSelectedId(incident.id);
                    document
                      .querySelector(".workspace")
                      ?.scrollIntoView({ behavior: "smooth", block: "center" });
                  }}
                >
                  <span className="row-location">
                    <span className="row-icon">
                      <MapPin size={17} />
                    </span>
                    <span>
                      <strong>{incident.area}</strong>
                      <small>
                        {incident.id} · {incident.roadSegment}
                      </small>
                    </span>
                  </span>
                  <span>
                    <ConfidenceBadge value={incident.confidence} />
                  </span>
                  <span className="row-sightings">
                    {incident.sightingCount.toString().padStart(2, "0")}
                  </span>
                  <span>
                    <span
                      className={`status-pill ${incident.status === "Verified" ? "status-verified" : incident.status === "Resolved" ? "status-resolved" : "status-review"}`}
                    >
                      {incident.status}
                    </span>
                  </span>
                  <span className="row-date">{incident.lastSeen.split(", ")[1]}</span>
                  <ChevronRight className="row-chevron" size={17} />
                </Button>
              ))
            ) : (
              <div className="list-empty">
                <Filter size={22} />
                <strong>No incidents found</strong>
                <p>Try another search or status filter.</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setQuery("");
                    setFilter("All incidents");
                  }}
                >
                  Clear filters
                </Button>
              </div>
            )}
          </div>
        </section>
        <footer className="footer">
          <span>© 2026 UrbanSense · Road intelligence</span>
          <span>
            <CircleHelp size={14} /> Demo dataset · Live municipal data
          </span>
        </footer>
      </main>
    </div>
  );
}
