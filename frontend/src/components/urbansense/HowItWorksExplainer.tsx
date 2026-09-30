import { ArrowRight, MapPin } from "lucide-react";
import potholeEvidenceImg from "@/assets/pothole-evidence.jpg";

export function HowItWorksExplainer() {
  return (
    <section className="gov-card explainer-card">
      <div className="explainer-header">
        <h3>How MIRA Works</h3>
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
              <span className="bbox-label">Pothole 87%</span>
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
