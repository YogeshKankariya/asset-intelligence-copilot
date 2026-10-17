import EvidencePanel from './EvidencePanel'

export default function MaintenanceRecurrenceCard({ data }) {
  const {
    asset_id,
    details = {},
    evidence = [],
    rule_or_calculation,
  } = data

  const rcaRequired = details.rca_required ?? false
  const groups = details.recurrent_groups || []

  return (
    <div className={`generative-card maintenance-card ${rcaRequired ? 'rca-required' : 'rca-normal'}`}>
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge asset-badge">{asset_id || 'WELL'}</span>
          <span className="card-subtitle">Corrective Maintenance Recurrence Analysis</span>
        </div>
        <div className={`status-pill ${rcaRequired ? 'pill-danger' : 'pill-success'}`}>
          {rcaRequired ? 'RCA REQUIRED' : 'NORMAL'}
        </div>
      </div>

      {rcaRequired ? (
        <div className="critical-alert-box" role="alert">
          <span className="alert-icon">⚠️</span>
          <div>
            <strong>Mandatory Compliance: Root-Cause Analysis (RCA) Required</strong>
            <p>
              Under T200 Section 10 and T350 Section 6, experiencing 3 or more corrective maintenance events
              on the same equipment kind within a rolling 12-month window mandates an engineering RCA before closing next repair.
            </p>
          </div>
        </div>
      ) : (
        <div className="success-banner">
          <span className="banner-icon">✅</span>
          <span>No equipment kind experienced 3 or more corrective repairs within any rolling 12-month period.</span>
        </div>
      )}

      {groups.length > 0 && (
        <div className="recurrent-groups-list">
          <h4 className="section-subtitle">Recurrent Equipment Breakdown</h4>
          {groups.map((g, idx) => (
            <div key={idx} className="group-card">
              <div className="group-header">
                <span className="group-equipment">🔧 {g.equipment_kind || 'Equipment'}</span>
                <span className="group-count-badge">{g.event_count} Corrective Events</span>
              </div>
              <div className="group-period">
                Period: <strong>{g.start_date}</strong> to <strong>{g.end_date}</strong>
              </div>
              {g.maintenance_ids && g.maintenance_ids.length > 0 && (
                <div className="group-records-row">
                  <span>Supporting Records:</span>
                  <div className="record-chips">
                    {g.maintenance_ids.map((mid, mIdx) => (
                      <span key={mIdx} className="record-chip">
                        {mid}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Operating Standard:</strong> {rule_or_calculation}
        </div>
      )}

      <div className="card-disclaimer">
        ℹ️ <strong>Compliance Distinction:</strong> An RCA requirement mandates investigation; it does not indicate
        that an RCA has already been conducted or approved.
      </div>

      <EvidencePanel evidence={evidence} />
    </div>
  )
}
