import EvidencePanel from './EvidencePanel'

export default function SafetyCompliancePanel({ data }) {
  const {
    asset_id,
    details = {},
    evidence = [],
    rule_or_calculation,
  } = data

  const wellType = details.well_type || 'Well'
  const tempLimit = details.high_temperature_limit_c || (wellType === 'T350' ? 95 : 85)
  const highTempAlarms = details.high_temperature_alarms || []
  const padSpills = details.pad_spills || []
  const reportableSpills = details.reportable_spills || []

  const hasHighTemp = highTempAlarms.length > 0
  const hasPadSpillShutIn = padSpills.length > 0
  const hasReportableSpill = reportableSpills.length > 0

  const hasAnyCritical = hasHighTemp || hasPadSpillShutIn || reportableSpills.some((s) => !s.filed_on_time)

  return (
    <div className={`generative-card safety-panel ${hasAnyCritical ? 'safety-alert' : 'safety-compliant'}`}>
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge asset-badge">{asset_id || 'WELL'}</span>
          <span className="card-badge type-badge">{wellType}</span>
          <span className="card-subtitle">Safety & Environmental Compliance Audit</span>
        </div>
        <div className={`status-pill ${hasAnyCritical ? 'pill-danger' : 'pill-success'}`}>
          {hasAnyCritical ? 'ACTION REQUIRED' : 'COMPLIANT'}
        </div>
      </div>

      <div className="compliance-sections-grid">
        {/* 1. High Temperature Alarms */}
        <div className={`compliance-block ${hasHighTemp ? 'block-alert' : 'block-ok'}`}>
          <div className="block-header">
            <span className="block-icon">🌡️</span>
            <div>
              <h4 className="block-title">High-Temperature Alarms</h4>
              <span className="block-meta">Threshold: &gt; {tempLimit}°C ({wellType} Manual)</span>
            </div>
            <span className={`block-status-pill ${hasHighTemp ? 'alarm' : 'ok'}`}>
              {hasHighTemp ? `${highTempAlarms.length} ALARM(S)` : 'NORMAL'}
            </span>
          </div>
          {hasHighTemp ? (
            <div className="block-content">
              {highTempAlarms.map((a, idx) => (
                <div key={idx} className="block-event-item">
                  <span className="event-badge">{a.inspection_id}</span>
                  <span className="event-reading">Reading: <strong>{a.wellhead_temp_c}°C</strong></span>
                  <p className="event-action">🚨 <strong>Mandatory Action:</strong> {a.action_required}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="block-ok-text">Wellhead temperatures remained within safe operating limits (≤ {tempLimit}°C).</p>
          )}
        </div>

        {/* 2. Pad Spill Shut-Ins */}
        <div className={`compliance-block ${hasPadSpillShutIn ? 'block-alert' : 'block-ok'}`}>
          <div className="block-header">
            <span className="block-icon">🛢️</span>
            <div>
              <h4 className="block-title">Pad Spill Shut-In Requirements</h4>
              <span className="block-meta">Threshold: &gt; 5% Pad Surface Area</span>
            </div>
            <span className={`block-status-pill ${hasPadSpillShutIn ? 'alarm' : 'ok'}`}>
              {hasPadSpillShutIn ? `${padSpills.length} SHUT-IN(S)` : 'CLEAR'}
            </span>
          </div>
          {hasPadSpillShutIn ? (
            <div className="block-content">
              {padSpills.map((s, idx) => (
                <div key={idx} className="block-event-item">
                  <span className="event-badge">{s.inspection_id}</span>
                  <span className="event-reading">Pad Coverage: <strong>{s.spill_area_pct}%</strong></span>
                  <p className="event-action">🛑 <strong>Mandatory Action:</strong> {s.action_required}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="block-ok-text">No uncorrected pad spills exceeding 5% surface area were recorded.</p>
          )}
        </div>

        {/* 3. Reportable Spills under SR-01 */}
        <div className={`compliance-block ${hasReportableSpill ? 'block-alert' : 'block-ok'}`}>
          <div className="block-header">
            <span className="block-icon">📄</span>
            <div>
              <h4 className="block-title">Reportable Spills (SOP SR-01)</h4>
              <span className="block-meta">Threshold: ≥ 5 bbl (24h Agency Notification)</span>
            </div>
            <span className={`block-status-pill ${hasReportableSpill ? 'alarm' : 'ok'}`}>
              {hasReportableSpill ? `${reportableSpills.length} REPORTABLE` : 'NONE'}
            </span>
          </div>
          {hasReportableSpill ? (
            <div className="block-content">
              {reportableSpills.map((sp, idx) => {
                const filingStatus = sp.filed_on_time
                  ? 'Filed on time'
                  : sp.proof_of_submission
                  ? 'Filed late'
                  : 'Unfiled / Missing Report'
                const hasNov = sp.notice_of_violation_issued
                return (
                  <div key={idx} className="block-event-item">
                    <div className="event-row">
                      <span className="event-badge">{sp.inspection_id}</span>
                      <span>Volume: <strong>{sp.est_volume_bbl} bbl</strong> ({sp.spill_class})</span>
                      <span className={`filing-tag ${sp.filed_on_time ? 'ontime' : 'late'}`}>
                        {filingStatus}
                      </span>
                    </div>
                    {hasNov && (
                      <div className="nov-alert-tag">
                        ⚠️ Notice of Violation Issued: {sp.notice_of_violation_ids?.join(', ')}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="block-ok-text">No reportable spills ≥ 5 bbl identified in inspection records.</p>
          )}
        </div>
      </div>

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Compliance Framework:</strong> {rule_or_calculation}
        </div>
      )}

      <EvidencePanel evidence={evidence} />
    </div>
  )
}
