import { Building2, Moon, Sun } from "lucide-react";

export function Header({
  theme = "light",
  onToggleTheme,
  scrollToTop,
}: {
  theme?: "dark" | "light";
  onToggleTheme?: () => void;
  scrollToTop?: () => void;
}) {
  return (
    <header className="gov-header">
      <div className="gov-header-inner">
        <div className="gov-brand" onClick={scrollToTop} title="Click to return to top">
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
  );
}
