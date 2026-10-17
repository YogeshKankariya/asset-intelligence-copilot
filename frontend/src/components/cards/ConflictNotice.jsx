export default function ConflictNotice({ conflicts, unresolvedConflicts }) {
  if (!conflicts || conflicts.length === 0) return null

  return (
    <div className="conflict-notice-container" role="alert">
      <div className="conflict-header">
        <span className="conflict-icon">⚠️</span>
        <span className="conflict-title">
          {unresolvedConflicts ? 'Unresolved Operational Conflict' : 'Disclosed Record Discrepancy'}
        </span>
      </div>
      <div className="conflict-list">
        {conflicts.map((c, idx) => (
          <div key={idx} className="conflict-item">
            <div className="conflict-item-row">
              <span className="conflict-field">Field: <code>{c.field || 'record'}</code></span>
              <span className={`conflict-status-pill ${c.is_resolved ? 'resolved' : 'unresolved'}`}>
                {c.is_resolved ? 'Resolved by Rule' : 'Unresolved'}
              </span>
            </div>
            <p className="conflict-description">{c.description}</p>
            {c.resolution && (
              <p className="conflict-resolution">
                <strong>Precedence:</strong> {c.resolution}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
