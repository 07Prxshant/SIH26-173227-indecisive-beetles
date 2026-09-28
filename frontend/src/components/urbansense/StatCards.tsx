import type { FilterValue } from "./types";

export function StatCards({
  counts,
  filter,
  onFilter,
}: {
  counts: { all: number; verified: number; review: number; high: number };
  filter: FilterValue;
  onFilter: (f: FilterValue) => void;
}) {
  return (
    <div className="gov-metrics-grid">
      <div
        className={`gov-metric-card ${filter === "All incidents" ? "active" : ""}`}
        onClick={() => onFilter("All incidents")}
      >
        <span className="metric-label">TOTAL REPORTED INCIDENTS</span>
        <div className="metric-num-row">
          <span className="metric-number">{counts.all}</span>
          <span className="metric-subtext">Active Database</span>
        </div>
      </div>

      <div
        className={`gov-metric-card ${filter === "Verified" ? "active" : ""}`}
        onClick={() => onFilter("Verified")}
      >
        <span className="metric-label">VERIFIED INCIDENTS</span>
        <div className="metric-num-row">
          <span className="metric-number text-gov-green">{counts.verified}</span>
          <span className="metric-subtext">Multi-Sighting Confirmed</span>
        </div>
      </div>

      <div
        className={`gov-metric-card ${filter === "Under review" ? "active" : ""}`}
        onClick={() => onFilter("Under review")}
      >
        <span className="metric-label">PENDING VERIFICATION</span>
        <div className="metric-num-row">
          <span className="metric-number text-gov-amber">{counts.review}</span>
          <span className="metric-subtext">Under Review</span>
        </div>
      </div>

      <div
        className={`gov-metric-card ${filter === "High priority" ? "active" : ""}`}
        onClick={() => onFilter("High priority")}
      >
        <span className="metric-label">HIGH PRIORITY</span>
        <div className="metric-num-row">
          <span className="metric-number text-gov-red">{counts.high}</span>
          <span className="metric-subtext">≥ 90% Confidence</span>
        </div>
      </div>
    </div>
  );
}
