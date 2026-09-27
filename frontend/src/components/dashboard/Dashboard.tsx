import { lazy, Suspense, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cpu,
  Crosshair,
  Eye,
  FileSpreadsheet,
  FileVideo,
  Filter,
  Loader2,
  MapPin,
  Play,
  Radio,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function VideoUploadCard({ onVideoProcessed }: { onVideoProcessed?: (incidents: any[]) => void }) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "completed" | "failed">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<{ frames?: number; sightings?: number; events?: number } | null>(null);

  const videoInputRef = useRef<HTMLInputElement>(null);
  const gpsInputRef = useRef<HTMLInputElement>(null);

  const handleProcessVideo = async () => {
    if (!selectedFile) return;
    setStatus("uploading");
    setMessage(`Uploading road footage (${selectedFile.name})...`);
    setStats(null);

    const formData = new FormData();
    formData.append("video", selectedFile);
    if (gpsFile) {
      formData.append("gps", gpsFile);
    }

    try {
      setStatus("processing");
      setMessage("Running YOLOv8 inference & ByteTrack multi-object tracking...");
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
      setMessage(data.message || "Video processed successfully!");
      setStats({
        frames: data.total_frames,
        sightings: data.potholes_detected,
        events: data.events_generated,
      });

      if (onVideoProcessed && data.incidents && data.incidents.length > 0) {
        onVideoProcessed(data.incidents);
      }
    } catch (err: any) {
      setStatus("failed");
      setMessage(err.message || "An error occurred during video processing.");
    }
  };

  return (
    <div className="upload-card-wrapper">
      <div className="upload-card">
        <div className="upload-header">
          <div className="upload-title-group">
            <div className="upload-icon-badge">
              <Cpu size={20} />
            </div>
            <div>
              <h3>Upload Road Video for YOLOv8 Pothole Detection</h3>
              <p>Feed real street video into the YOLOv8 + ByteTrack pipeline for automated spatial verification</p>
            </div>
          </div>
          <div className="upload-tag-badge">
            <Sparkles size={12} /> SIH 2026 PIPELINE
          </div>
        </div>

        <input
          type="file"
          ref={videoInputRef}
          style={{ display: "none" }}
          accept="video/*,.mp4,.avi,.mov,.mkv"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              setSelectedFile(e.target.files[0]);
              setStatus("idle");
              setMessage(null);
            }
          }}
        />

        <input
          type="file"
          ref={gpsInputRef}
          style={{ display: "none" }}
          accept=".csv,.gpx"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              setGpsFile(e.target.files[0]);
            }
          }}
        />

        <div className="upload-dropzone-grid">
          <div
            className={`dropzone-box ${selectedFile ? "dropzone-active" : ""}`}
            onClick={() => videoInputRef.current?.click()}
          >
            <div className="dropzone-info">
              <FileVideo className="dropzone-icon" size={24} />
              <div className="dropzone-text">
                <strong>{selectedFile ? selectedFile.name : "Select Road Video File"}</strong>
                <span>{selectedFile ? `${formatFileSize(selectedFile.size)} · MP4` : "Click to select .mp4, .avi, .mov footage"}</span>
              </div>
            </div>
            {selectedFile && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  setStatus("idle");
                  setMessage(null);
                }}
              >
                <X size={15} />
              </Button>
            )}
          </div>

          <div
            className={`dropzone-box ${gpsFile ? "dropzone-active" : ""}`}
            onClick={() => gpsInputRef.current?.click()}
          >
            <div className="dropzone-info">
              <FileSpreadsheet className="dropzone-icon" size={22} />
              <div className="dropzone-text">
                <strong>{gpsFile ? gpsFile.name : "GPS Trace (Optional)"}</strong>
                <span>{gpsFile ? formatFileSize(gpsFile.size) : "Synchronize coordinates (.csv)"}</span>
              </div>
            </div>
            {gpsFile && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  setGpsFile(null);
                }}
              >
                <X size={15} />
              </Button>
            )}
          </div>

          <button
            className="btn-process"
            onClick={handleProcessVideo}
            disabled={!selectedFile || status === "uploading" || status === "processing"}
          >
            {status === "uploading" || status === "processing" ? (
              <>
                <Loader2 size={18} className="animate-spin" /> Processing...
              </>
            ) : (
              <>
                <Play size={16} /> Process Video
              </>
            )}
          </button>
        </div>

        {(status === "uploading" || status === "processing") && (
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: status === "uploading" ? "40%" : "85%" }} />
          </div>
        )}

        {message && (
          <div className={`processing-banner ${status === "completed" ? "banner-success" : status === "failed" ? "banner-error" : "banner-processing"}`}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {status === "completed" && <Check size={18} />}
              {status === "failed" && <X size={18} />}
              {(status === "uploading" || status === "processing") && <Loader2 size={18} className="animate-spin" />}
              <span>{message}</span>
            </div>

            {stats && (
              <div style={{ display: "flex", gap: "12px", fontSize: "0.8rem", fontWeight: 600 }}>
                <span>{stats.frames} Frames</span>
                <span>·</span>
                <span>{stats.sightings} Sightings</span>
                <span>·</span>
                <span>{stats.events} Kafka Events</span>
              </div>
            )}
          </div>
        )}
      </div>
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
        <div className="dual-confidence-wrapper">
          <div className="confidence-box">
            <div className="confidence-box-title">YOLO DETECTOR</div>
            <div className="confidence-box-value">
              {incident.detectorConfidence ?? incident.confidence}%
            </div>
          </div>
          <div className="confidence-box">
            <div className="confidence-box-title">POSTGIS FUSED</div>
            <div className="confidence-box-value confidence-box-highlight">
              {incident.confidence}%
            </div>
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
            <CircleHelp size={14} /> Live municipal dataset
          </span>
        </footer>
      </main>
    </div>
  );
}
