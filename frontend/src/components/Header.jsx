import { useAssistant } from '../context/useAssistant'

export default function Header({ onToggleSidebar }) {
  const { currentView, activeWellId, setActiveWellId, backendHealthy } = useAssistant()

  const viewTitles = {
    copilot: 'Operational Intelligence Copilot',
    operations: 'Well Operations & Telemetry Directory',
    evidence: 'Evidence & Session Activity Log',
  }

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation menu"
        >
          ☰
        </button>
        <div className="view-title-group">
          <h2 className="view-title">{viewTitles[currentView] || 'Asset Intelligence'}</h2>
          <span className="view-subtitle">Grounded in physical thresholds &amp; inspection records</span>
        </div>
      </div>

      <div className="header-right">
        {activeWellId && (
          <div className="active-well-pill">
            <span className="well-pill-label">Scope:</span>
            <span className="well-pill-id">{activeWellId}</span>
            <button
              type="button"
              className="well-pill-clear"
              onClick={() => setActiveWellId(null)}
              aria-label="Clear active well scope"
            >
              ×
            </button>
          </div>
        )}

        <div className={`health-badge ${backendHealthy ? 'online' : 'offline'}`}>
          <span className="health-dot"></span>
          <span>{backendHealthy ? 'API ONLINE' : 'DISCONNECTED'}</span>
        </div>
      </div>
    </header>
  )
}
