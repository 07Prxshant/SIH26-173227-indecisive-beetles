import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUp,
  Building2,
  Check,
  ChevronRight,
  Clock,
  Crosshair,
  Eye,
  FileSpreadsheet,
  FileVideo,
  Loader2,
  MapPin,
  Maximize2,
  Minimize2,
  Navigation,
  Play,
  Radio,
  Search,
  Upload,
  X,
} from "lucide-react";
import { ClientOnly } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { apiBaseUrl, toDashboardIncident, useLiveIncidents } from "@/lib/incident-api";
import type { Incident } from "@/types/incident";
import potholeEvidenceImg from "@/assets/pothole-evidence.jpg";

const IncidentMap = lazy(() => import("@/map/IncidentMap"));
type FilterValue = "All incidents" | "Verified" | "Under review" | "Resolved";
type LocationMode = "search" | "device";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function HowItWorksExplainer() {
  return (
    <section className="gov-card explainer-card">
      <div className="explainer-header">
        <h3>How UrbanSense Works</h3>
        <p>Road footage is analysed to detect potholes, associate their location and create incidents for review.</p>
      </div>

      <div className="explainer-stages">
        {/* Stage 1 */}
        <div className="stage-item">
          <div className="stage-badge">1</div>
          <div className="stage-media">
            <img src={potholeEvidenceImg} alt="Sample road footage" />
            <span className="stage-overlay-tag">Input Video</span>
          </div>
          <div className="stage-info">
            <h4>Road Footage</h4>
            <p>Road video is submitted for analysis.</p>
          </div>
        </div>

        <div className="stage-arrow">
          <ArrowRight size={20} />
        </div>

        {/* Stage 2 */}
        <div className="stage-item">
          <div className="stage-badge">2</div>
          <div className="stage-media">
            <img src={potholeEvidenceImg} alt="YOLOv8 pothole detection" />
            <div className="stage-bounding-box" style={{ top: '35%', left: '30%', width: '40%', height: '35%' }}>
              <span className="bbox-label">Pothole (87%)</span>
            </div>
          </div>
          <div className="stage-info">
            <h4>Pothole Detection</h4>
            <p>YOLOv8 identifies and tracks potholes in the footage.</p>
          </div>
        </div>

        <div className="stage-arrow">
          <ArrowRight size={20} />
        </div>

        {/* Stage 3 */}
        <div className="stage-item">
          <div className="stage-badge">3</div>
          <div className="stage-media stage-map-preview">
            <div className="mini-map-visual">
              <MapPin size={24} className="text-gov-red animate-bounce" />
              <span className="map-pin-tag">Incident Logged</span>
            </div>
          </div>
          <div className="stage-info">
            <h4>Incident Location</h4>
            <p>Detected incidents are associated with a location and displayed on the incident map.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function VideoUploadCard({ onVideoProcessed }: { onVideoProcessed?: (incidents: any[]) => void }) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);

  // Location mode state
  const [locationMode, setLocationMode] = useState<LocationMode>("search");
  const [searchQuery, setSearchQuery] = useState("Khan Market, New Delhi");
  const [geocodedLocation, setGeocodedLocation] = useState<{ lat: number; lon: number; name: string } | null>({
    lat: 28.6003,
    lon: 77.2270,
    name: "Khan Market, New Delhi",
  });
  const [isGeocoding, setIsGeocoding] = useState(false);

  // Device location state
  const [deviceLocation, setDeviceLocation] = useState<{ lat: number; lon: number; accuracy?: number; placeName: string } | null>(null);
  const [deviceLocStatus, setDeviceLocStatus] = useState<"idle" | "requesting" | "success" | "error">("idle");

  // Processing state
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "completed" | "failed">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<{ frames?: number; sightings?: number; events?: number } | null>(null);

  const videoInputRef = useRef<HTMLInputElement>(null);
  const gpsInputRef = useRef<HTMLInputElement>(null);

  // Perform geocoding lookup for place search query
  const geocodePlaceSearch = async (queryStr: string) => {
    if (!queryStr.trim()) return;
    setIsGeocoding(true);

    try {
      const coordMatch = queryStr.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
      if (coordMatch) {
        const lat = parseFloat(coordMatch[1]);
        const lon = parseFloat(coordMatch[2]);
        if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
          setGeocodedLocation({ lat, lon, name: `Coordinates (${lat.toFixed(4)}, ${lon.toFixed(4)})` });
          setIsGeocoding(false);
          return;
        }
      }

      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(queryStr)}&limit=1`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          const lat = parseFloat(data[0].lat);
          const lon = parseFloat(data[0].lon);
          const displayName = data[0].display_name.split(",").slice(0, 3).join(",");
          setGeocodedLocation({ lat, lon, name: displayName });
          setIsGeocoding(false);
          return;
        }
      }
    } catch (err) {
      console.warn("Geocoding lookup error:", err);
    }

    setGeocodedLocation({ lat: 28.6003, lon: 77.2270, name: `${queryStr} (Location set)` });
    setIsGeocoding(false);
  };

  useEffect(() => {
    if (locationMode !== "search") return;
    const timer = setTimeout(() => {
      geocodePlaceSearch(searchQuery);
    }, 600);
    return () => clearTimeout(timer);
  }, [searchQuery, locationMode]);

  const activeLocation = useMemo(() => {
    if (locationMode === "device" && deviceLocation) {
      return { lat: deviceLocation.lat, lon: deviceLocation.lon, name: deviceLocation.placeName, valid: true };
    }
    if (geocodedLocation) {
      return { lat: geocodedLocation.lat, lon: geocodedLocation.lon, name: geocodedLocation.name, valid: true };
    }
    return { lat: 28.6003, lon: 77.2270, name: "Khan Market, New Delhi", valid: true };
  }, [locationMode, deviceLocation, geocodedLocation]);

  const requestDeviceLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      setDeviceLocation({ lat: 28.6003, lon: 77.2270, accuracy: 25, placeName: "Khan Market, New Delhi" });
      setDeviceLocStatus("success");
      return;
    }

    setDeviceLocStatus("requesting");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = Math.round(position.coords.latitude * 10000) / 10000;
        const lon = Math.round(position.coords.longitude * 10000) / 10000;
        const acc = position.coords.accuracy ? Math.round(position.coords.accuracy) : undefined;
        setDeviceLocation({ lat, lon, accuracy: acc, placeName: "Current Device Location" });
        setDeviceLocStatus("success");
      },
      () => {
        setDeviceLocation({ lat: 28.6003, lon: 77.2270, accuracy: 50, placeName: "Municipal Location Center" });
        setDeviceLocStatus("success");
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 }
    );
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) return;

    setStatus("uploading");
    setMessage("Uploading road footage to inspection server...");
    setStats(null);

    try {
      const formData = new FormData();
      formData.append("video", selectedFile);
      if (gpsFile) {
        formData.append("gps", gpsFile);
      }

      if (activeLocation.valid) {
        formData.append("latitude", activeLocation.lat.toString());
        formData.append("longitude", activeLocation.lon.toString());
      }

      setStatus("processing");
      setMessage("Running YOLOv8 & ByteTrack pothole detection pipeline...");

      const response = await fetch(`${apiBaseUrl}/videos/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || `Server responded with status ${response.status}`);
      }

      const result = await response.json();
      setStatus("completed");
      setMessage(result.message || "Incident mapped for road maintenance review.");
      setStats({
        frames: result.total_frames,
        sightings: result.potholes_detected,
        events: result.events_generated,
      });

      if (onVideoProcessed && Array.isArray(result.incidents)) {
        onVideoProcessed(result.incidents);
      }
    } catch (err: any) {
      console.error("Video processing failed:", err);
      setStatus("failed");
      setMessage(err.message || "Video analysis failed. Please retry.");
    }
  };

  return (
    <div className="gov-card upload-portal-card">
      <div className="gov-card-header">
        <div>
          <h3>Road Video Analysis</h3>
          <p className="gov-card-subtitle">
            Upload road footage for pothole detection and geographic incident mapping.
          </p>
        </div>
      </div>

      <div className="gov-card-body">
        {/* Step 1: Select Road Video */}
        <div className="form-group">
          <label className="form-label">
            <span className="form-step">1</span> Select Road Video
          </label>
          <div
            className={`gov-file-dropzone ${selectedFile ? "active" : ""}`}
            onClick={() => videoInputRef.current?.click()}
          >
            <input
              ref={videoInputRef}
              type="file"
              accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  setStatus("idle");
                  setMessage(null);
                }
              }}
            />
            {selectedFile ? (
              <div className="selected-file-row">
                <FileVideo size={20} className="text-gov-green" />
                <div className="file-details">
                  <span className="file-name">{selectedFile.name}</span>
                  <span className="file-meta">{formatFileSize(selectedFile.size)}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="file-remove-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    if (videoInputRef.current) videoInputRef.current.value = "";
                  }}
                >
                  <X size={14} /> Remove
                </Button>
              </div>
            ) : (
              <div className="dropzone-text-group">
                <Upload size={22} className="text-gov-subtle" />
                <div>
                  <strong>Click to choose video file</strong> (MP4, AVI, MOV, WEBM)
                  <p>Upload road inspection video file</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Step 2: Video Location */}
        <div className="form-group">
          <label className="form-label">
            <span className="form-step">2</span> Video Location
          </label>
          <p className="form-help-text">Select the location associated with this road footage.</p>

          <div className="location-radio-group">
            <label className="gov-radio-label">
              <input
                type="radio"
                name="locMode"
                checked={locationMode === "search"}
                onChange={() => setLocationMode("search")}
              />
              <span>Enter location manually</span>
            </label>

            <label className="gov-radio-label">
              <input
                type="radio"
                name="locMode"
                checked={locationMode === "device"}
                onChange={() => {
                  setLocationMode("device");
                  if (!deviceLocation) requestDeviceLocation();
                }}
              />
              <span>Use my current device location</span>
            </label>
          </div>

          {locationMode === "search" && (
            <div className="location-input-subgroup">
              <div className="search-field-gov">
                <Search size={15} className="search-icon-gov" />
                <input
                  type="text"
                  className="gov-input"
                  placeholder="Search address, locality or coordinates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {isGeocoding && <Loader2 size={15} className="animate-spin clear-icon-gov" />}
              </div>
            </div>
          )}

          {locationMode === "device" && (
            <div className="location-device-subgroup">
              {deviceLocStatus === "requesting" ? (
                <div className="device-loc-banner loading">
                  <Loader2 size={16} className="animate-spin" />
                  <span>Retrieving device GPS coordinates...</span>
                </div>
              ) : (
                <div className="device-loc-banner success">
                  <Navigation size={16} />
                  <div>
                    <strong>{deviceLocation?.placeName || "Device Location"}</strong>
                    <span>Lat: {activeLocation.lat.toFixed(4)} | Lon: {activeLocation.lon.toFixed(4)}</span>
                  </div>
                  <Button variant="outline" size="sm" onClick={requestDeviceLocation} className="btn-secondary-gov">
                    Re-locate
                  </Button>
                </div>
              )}
            </div>
          )}

          <div className="location-confirmed-bar">
            <MapPin size={14} className="text-gov-green" />
            <span>
              Selected Location: <strong>{activeLocation.name}</strong> (Coordinates: {activeLocation.lat.toFixed(4)}, {activeLocation.lon.toFixed(4)})
            </span>
          </div>
        </div>

        {/* Step 3: GPS Track (Optional) */}
        <div className="form-group form-group-optional">
          <div className="optional-title-row">
            <span className="optional-tag">Optional</span>
            <span>GPS Track (Optional)</span>
          </div>
          <p className="form-help-text">Upload a GPS track when location data is available with the road footage.</p>
          <input
            ref={gpsInputRef}
            type="file"
            accept=".csv,.gpx"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setGpsFile(e.target.files[0]);
              }
            }}
          />
          {gpsFile ? (
            <div className="gps-file-badge">
              <FileSpreadsheet size={14} />
              <span>{gpsFile.name}</span>
              <button
                type="button"
                onClick={() => {
                  setGpsFile(null);
                  if (gpsInputRef.current) gpsInputRef.current.value = "";
                }}
              >
                <X size={12} />
              </button>
            </div>
          ) : (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="btn-tertiary-gov"
              onClick={() => gpsInputRef.current?.click()}
            >
              <FileSpreadsheet size={13} /> Upload GPS Track
            </Button>
          )}
        </div>

        {/* Primary Action Button */}
        <div className="form-action-row">
          <Button
            className="btn-primary-gov btn-strong-primary"
            disabled={!selectedFile || status === "uploading" || status === "processing"}
            onClick={handleUploadAndProcess}
          >
            {status === "uploading" || status === "processing" ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Processing Video...</span>
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" />
                <span>Process Video</span>
              </>
            )}
          </Button>

          {message && (
            <div className={`gov-alert alert-${status}`}>
              {status === "completed" && <Check size={15} />}
              {status === "failed" && <X size={15} />}
              {(status === "uploading" || status === "processing") && <Loader2 size={15} className="animate-spin" />}
              <span>{message}</span>
            </div>
          )}

          {stats && (
            <div className="admin-stats-summary">
              <div className="stat-box">
                <span className="stat-num">{stats.frames}</span>
                <span className="stat-lbl">Frames Analyzed</span>
              </div>
              <div className="stat-box highlight">
                <span className="stat-num">{stats.sightings}</span>
                <span className="stat-lbl">Potholes Detected</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{stats.events}</span>
                <span className="stat-lbl">Events Logged</span>
              </div>
            </div>
          )}
        </div>
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
      <div className="detail-empty-gov">
        <Crosshair size={28} className="text-gov-subtle" />
        <h4>Select an Incident Record</h4>
        <p>Click on any map marker or list entry to inspect detailed incident record data.</p>
      </div>
    );

  return (
    <div className="detail-record-wrap" key={incident.id}>
      <div className="detail-record-header">
        <div>
          <span className="detail-record-eyebrow">INCIDENT RECORD</span>
          <h3>{incident.id}</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Close details"
          onClick={onClose}
          className="btn-icon-gov"
        >
          <X size={15} />
        </Button>
      </div>

      <div className="detail-status-banner">
        <span className={`gov-status-pill pill-${incident.status.toLowerCase().replace(" ", "-")}`}>
          {incident.status === "Verified" && <Check size={12} />}
          {incident.status}
        </span>
        <span className="record-area-name">{incident.area}</span>
      </div>

      {incident.image ? (
        <div className="evidence-frame-box">
          <img
            src={incident.image}
            alt="Representative detection frame"
            loading="lazy"
            width={1024}
            height={768}
          />
          <span className="evidence-label">DETECTION FRAME EVIDENCE</span>
        </div>
      ) : (
        <div className="no-evidence-box">
          <Eye size={16} /> No evidence frame image attached
        </div>
      )}

      <div className="record-grid">
        <div className="record-field">
          <span className="field-name">Incident ID</span>
          <span className="field-value font-mono">{incident.id}</span>
        </div>

        <div className="record-field">
          <span className="field-name">Type</span>
          <span className="field-value">Pothole Hazard</span>
        </div>

        <div className="record-field">
          <span className="field-name">Status</span>
          <span className="field-value">{incident.status}</span>
        </div>

        <div className="record-field">
          <span className="field-name">Road Segment</span>
          <span className="field-value">{incident.roadSegment}</span>
        </div>

        <div className="record-field">
          <span className="field-name">Coordinates</span>
          <span className="field-value font-mono">
            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </span>
        </div>

        <div className="record-field">
          <span className="field-name">Detector Confidence</span>
          <span className="field-value">{incident.detectorConfidence ?? incident.confidence}%</span>
        </div>

        <div className="record-field">
          <span className="field-name">Incident Confidence</span>
          <span className="field-value text-gov-green font-bold">{incident.confidence}%</span>
        </div>

        <div className="record-field">
          <span className="field-name">Sightings</span>
          <span className="field-value">{incident.sightingCount}</span>
        </div>

        <div className="record-field">
          <span className="field-name">First Detected</span>
          <span className="field-value">{incident.firstSeen}</span>
        </div>

        <div className="record-field">
          <span className="field-name">Last Detected</span>
          <span className="field-value">{incident.lastSeen}</span>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { incidents, addIncidents } = useLiveIncidents();
  const [selectedId, setSelectedId] = useState<string | null>(() => incidents[0]?.id ?? null);
  const [filter, setFilter] = useState<FilterValue>("All incidents");
  const [query, setQuery] = useState("");
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const selected = incidents.find((item) => item.id === selectedId);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const filtered = useMemo(
    () =>
      incidents.filter(
        (item) =>
          (filter === "All incidents" || item.status === filter) &&
          `${item.id} ${item.area} ${item.roadSegment}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [filter, incidents, query],
  );

  const verifiedCount = incidents.filter((item) => item.status === "Verified").length;
  const pendingCount = incidents.filter((item) => item.status === "Under review").length;
  const highPriorityCount = incidents.filter(
    (item) => item.confidence >= 90 && item.status !== "Resolved",
  ).length;

  return (
    <div className="gov-app">
      {/* Header */}
      <header className="gov-header">
        <div className="gov-header-inner">
          <div className="gov-brand" onClick={scrollToTop} title="Click to scroll to top">
            <span className="gov-brand-icon">
              <Building2 size={18} />
            </span>
            <div className="gov-brand-titles">
              <span className="brand-main">UrbanSense</span>
              <span className="brand-sub">Municipal Road Condition Monitoring System</span>
            </div>
          </div>

          <div className="gov-header-right">
            <div className="system-status-indicator">
              <span className="status-dot-green" />
              <span>System Status: Operational</span>
            </div>
            <span className="header-divider-v" />
            <span className="prototype-tag">SIH 2026 Prototype</span>
            <span className="header-divider-v" />
            <nav className="header-nav-links">
              <button type="button" className="nav-link-gov">Help</button>
              <button type="button" className="nav-link-gov">Accessibility</button>
              <button type="button" className="nav-link-gov">EN</button>
            </nav>
          </div>
        </div>
      </header>

      <div className="gov-container">
        {/* Breadcrumb */}
        <nav className="gov-breadcrumb" aria-label="Breadcrumb">
          <span>Home</span>
          <ChevronRight size={13} />
          <span className="current">Road Monitoring</span>
        </nav>

        {/* Operational Page Title */}
        <div className="gov-page-heading">
          <h2>Road Condition Monitoring</h2>
          <p>Monitor pothole detections, verify road incidents and view their geographic distribution.</p>
        </div>

        {/* How UrbanSense Works 3-Stage Explainer */}
        <HowItWorksExplainer />

        {/* Summary Metric Cards */}
        <div className="gov-metrics-grid">
          <div className="gov-metric-card">
            <span className="metric-label">TOTAL REPORTED INCIDENTS</span>
            <div className="metric-num-row">
              <span className="metric-number">{incidents.length}</span>
              <span className="metric-subtext">Active Database</span>
            </div>
          </div>

          <div className="gov-metric-card">
            <span className="metric-label">VERIFIED INCIDENTS</span>
            <div className="metric-num-row">
              <span className="metric-number text-gov-green">{verifiedCount}</span>
              <span className="metric-subtext">Multi-Sighting Confirmed</span>
            </div>
          </div>

          <div className="gov-metric-card">
            <span className="metric-label">PENDING VERIFICATION</span>
            <div className="metric-num-row">
              <span className="metric-number text-gov-amber">{pendingCount}</span>
              <span className="metric-subtext">Under Review</span>
            </div>
          </div>

          <div className="gov-metric-card">
            <span className="metric-label">HIGH PRIORITY</span>
            <div className="metric-num-row">
              <span className="metric-number text-gov-red">{highPriorityCount}</span>
              <span className="metric-subtext">≥ 90% Confidence</span>
            </div>
          </div>
        </div>

        {/* Road Video Analysis Workflow */}
        <VideoUploadCard
          onVideoProcessed={(newApiIncidents) => {
            if (newApiIncidents && newApiIncidents.length > 0) {
              addIncidents(newApiIncidents);
              const first = toDashboardIncident(newApiIncidents[0]);
              setSelectedId(first.id);
            }
          }}
        />

        {/* Prominent Road Incident Map Section */}
        <div className="gov-section-header">
          <div>
            <h3>Road Incident Map</h3>
            <span className="section-sub">Geographic distribution of detected road incidents</span>
          </div>
          <div className="map-legend-gov">
            <span><i className="dot dot-red" /> High Priority</span>
            <span><i className="dot dot-amber" /> Medium</span>
            <span><i className="dot dot-green" /> Verified / Resolved</span>
          </div>
        </div>

        <div className={`gov-workspace ${isMapExpanded ? "expanded" : ""}`}>
          <section className="gov-map-panel" aria-label="Road incidents map">
            <div className="gov-panel-toolbar">
              <div className="toolbar-title">
                <MapPin size={15} /> Active Spatial Region
              </div>
              <div className="toolbar-controls">
                <span className="count-tag">{filtered.length} locations displayed</span>
                <Button
                  variant="outline"
                  size="sm"
                  className="btn-secondary-gov"
                  onClick={() => setIsMapExpanded(!isMapExpanded)}
                  title={isMapExpanded ? "Collapse to side view" : "Expand map canvas"}
                >
                  {isMapExpanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                  <span>{isMapExpanded ? "Standard View" : "Expand Map"}</span>
                </Button>
              </div>
            </div>

            <div className="gov-map-container">
              <ClientOnly fallback={<div className="map-loading-gov">Loading OpenStreetMap Canvas…</div>}>
                <Suspense fallback={<div className="map-loading-gov">Loading OpenStreetMap Canvas…</div>}>
                  <IncidentMap incidents={filtered} selected={selected} onSelect={setSelectedId} />
                </Suspense>
              </ClientOnly>
            </div>
            <div className="gov-map-footer">
              <span>OpenStreetMap GIS Engine</span>
              <span>Click marker to view incident details</span>
            </div>
          </section>

          <aside className="gov-detail-panel" aria-label="Incident details panel">
            <IncidentPanel incident={selected} onClose={() => setSelectedId(null)} />
          </aside>
        </div>

        {/* Administrative Incident Data Table */}
        <section className="gov-table-section">
          <div className="table-section-header">
            <div>
              <h3>Incident Log & Records</h3>
              <p className="table-sub">Filter and review logged pothole detection records</p>
            </div>

            <div className="table-filter-bar">
              <div className="table-search-box">
                <Search size={14} className="search-icon" />
                <input
                  type="text"
                  className="gov-input"
                  placeholder="Filter by ID, area, or road segment..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>

              <div className="status-filter-group">
                {(["All incidents", "Verified", "Under review", "Resolved"] as FilterValue[]).map((statusOpt) => (
                  <button
                    key={statusOpt}
                    type="button"
                    className={`btn-filter-tag ${filter === statusOpt ? "active" : ""}`}
                    onClick={() => setFilter(statusOpt)}
                  >
                    {statusOpt}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="table-wrapper">
            <table className="gov-data-table">
              <thead>
                <tr>
                  <th>INCIDENT ID</th>
                  <th>LOCATION / ROAD SEGMENT</th>
                  <th>CONFIDENCE</th>
                  <th>SIGHTINGS</th>
                  <th>STATUS</th>
                  <th>LAST DETECTED</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length ? (
                  filtered.map((incident) => (
                    <tr
                      key={incident.id}
                      className={selectedId === incident.id ? "row-selected" : ""}
                      onClick={() => {
                        setSelectedId(incident.id);
                        document
                          .querySelector(".gov-workspace")
                          ?.scrollIntoView({ behavior: "smooth", block: "center" });
                      }}
                    >
                      <td className="font-mono font-bold text-gov-green">{incident.id}</td>
                      <td>
                        <strong>{incident.area}</strong>
                        <div className="table-subtext">{incident.roadSegment}</div>
                      </td>
                      <td>
                        <span className={`gov-conf-badge conf-${incident.confidence >= 90 ? "high" : incident.confidence >= 80 ? "medium" : "low"}`}>
                          {incident.confidence}%
                        </span>
                      </td>
                      <td>{incident.sightingCount}</td>
                      <td>
                        <span className={`gov-status-pill pill-${incident.status.toLowerCase().replace(" ", "-")}`}>
                          {incident.status}
                        </span>
                      </td>
                      <td className="table-date">{incident.lastSeen.split(", ")[1] || incident.lastSeen}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="btn-table-action"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedId(incident.id);
                            document
                              .querySelector(".gov-workspace")
                              ?.scrollIntoView({ behavior: "smooth", block: "center" });
                          }}
                        >
                          View Record
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="table-empty">
                      No matching incident records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Footer */}
        <footer className="gov-footer">
          <div className="footer-left">
            <span className="footer-title">UrbanSense</span>
            <span>Municipal Road Condition Monitoring System</span>
          </div>

          <div className="footer-right">
            <span>Smart India Hackathon 2026 Prototype</span>
            <span className="footer-slash">•</span>
            <span>For Demonstration Purposes Only</span>
          </div>
        </footer>
      </div>

      {/* Floating Scroll Top */}
      <button
        type="button"
        className="gov-scroll-top"
        onClick={scrollToTop}
        title="Scroll to top"
        aria-label="Scroll to top"
      >
        <ArrowUp size={16} />
      </button>
    </div>
  );
}
