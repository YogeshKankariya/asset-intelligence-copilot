import { useAssistant } from '../context/useAssistant'

export default function Sidebar({ isOpen, onClose }) {
  const {
    currentView,
    setCurrentView,
    activeWellId,
    setActiveWellId,
    wells,
    messages,
    clearMessages,
    sendMessage,
    backendHealthy,
  } = useAssistant()

  const navItems = [
    { id: 'copilot', label: 'Copilot', icon: '💬' },
    { id: 'operations', label: 'Well Operations', icon: '⚙️' },
    { id: 'evidence', label: 'Evidence & Activity', icon: '📜' },
  ]

  // Extract recent user queries for session history
  const userQueries = messages
    .filter((m) => m.sender === 'user')
    .map((m) => ({ id: m.id, text: m.text, assetId: m.asset_id }))
    .slice(-8)

  return (
    <>
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} aria-hidden="true" />}
      <aside className={`app-sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-logo-wrap">
            <span className="brand-icon">⚡</span>
          </div>
          <div className="brand-text">
            <h1 className="brand-title">Asset Intelligence</h1>
            <span className="brand-badge">COPILOT v1.0</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <span className="nav-section-title">Navigation</span>
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-button ${currentView === item.id ? 'active' : ''}`}
              onClick={() => {
                setCurrentView(item.id)
                if (window.innerWidth < 768) onClose()
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Active Well Scoping */}
        <div className="sidebar-section">
          <div className="section-header-row">
            <span className="nav-section-title">Active Well Scope</span>
            {activeWellId && (
              <button
                type="button"
                className="clear-well-btn"
                onClick={() => setActiveWellId(null)}
                title="Clear well filter"
              >
                Clear
              </button>
            )}
          </div>
          <select
            className="well-select-dropdown"
            value={activeWellId || ''}
            onChange={(e) => setActiveWellId(e.target.value || null)}
          >
            <option value="">All Wells (No Filter)</option>
            {wells.slice(0, 50).map((w) => (
              <option key={w.asset_id} value={w.asset_id}>
                {w.asset_id} {w.well_type ? `(${w.well_type})` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Session Query History */}
        <div className="sidebar-section session-history-section">
          <div className="section-header-row">
            <span className="nav-section-title">Session Queries ({userQueries.length})</span>
            {userQueries.length > 0 && (
              <button
                type="button"
                className="clear-history-btn"
                onClick={clearMessages}
                title="Clear session history"
              >
                Reset
              </button>
            )}
          </div>

          <div className="history-list">
            {userQueries.length === 0 ? (
              <p className="empty-history-text">No queries in current session.</p>
            ) : (
              userQueries.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  className="history-item-btn"
                  onClick={() => {
                    setCurrentView('copilot')
                    sendMessage(q.text, q.assetId)
                    if (window.innerWidth < 768) onClose()
                  }}
                  title={q.text}
                >
                  <span className="history-icon">↩</span>
                  <span className="history-text">{q.text}</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Footer with connection status */}
        <div className="sidebar-footer">
          <div className="connection-status-row">
            <span className={`status-indicator-dot ${backendHealthy ? 'online' : 'offline'}`}></span>
            <span className="status-text">
              Backend {backendHealthy === null ? 'Checking...' : backendHealthy ? 'Connected (Port 8000)' : 'Disconnected'}
            </span>
          </div>
          <span className="dataset-integrity-tag">Read-only operational dataset</span>
        </div>
      </aside>
    </>
  )
}
