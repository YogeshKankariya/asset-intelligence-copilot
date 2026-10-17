import EvidencePanel from './EvidencePanel'

export default function ConsecutiveDowntimeCard({ data }) {
  const {
    asset_id,
    details = {},
    evidence = [],
    rule_or_calculation,
  } = data

  const maxConsecutive = details.max_consecutive_days ?? 0
  const thresholdDays = details.consecutive_days_threshold ?? 14
  const thresholdExceeded = details.threshold_exceeded ?? (maxConsecutive > thresholdDays)

  return (
    <div className={`generative-card consecutive-card ${thresholdExceeded ? 'alert-critical' : 'status-normal'}`}>
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge asset-badge">{asset_id || 'WELL'}</span>
          <span className="card-subtitle">Consecutive Downtime Monitoring</span>
        </div>
        <div className={`status-pill ${thresholdExceeded ? 'pill-danger' : 'pill-success'}`}>
          {thresholdExceeded ? 'SUPERVISOR ALERT' : 'WITHIN THRESHOLD'}
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric-box hero-metric">
          <span className="metric-label">Max Consecutive Streak</span>
          <span className={`metric-number ${thresholdExceeded ? 'text-crimson' : 'text-emerald'}`}>
            {maxConsecutive}
          </span>
          <span className="metric-unit">Consecutive Days</span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Reporting Threshold</span>
          <span className="metric-number">{thresholdDays}</span>
          <span className="metric-unit">Days Limit</span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Inspection Streak</span>
          <span className="metric-number">
            {Math.floor(maxConsecutive / 7)}
          </span>
          <span className="metric-subtext">Consecutive Weeks</span>
        </div>
      </div>

      {thresholdExceeded ? (
        <div className="critical-alert-box" role="alert">
          <span className="alert-icon">🚨</span>
          <div>
            <strong>Mandatory Action: Supervisor Notification Required</strong>
            <p>
              Well {asset_id} experienced {maxConsecutive} consecutive days of non-producing status,
              breaching the {thresholdDays}-day limit defined in field operating standards.
            </p>
          </div>
        </div>
      ) : (
        <div className="success-banner">
          <span className="banner-icon">✅</span>
          <span>No consecutive downtime streak exceeded the {thresholdDays}-day escalation threshold.</span>
        </div>
      )}

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Standard Rule:</strong> {rule_or_calculation}
        </div>
      )}

      <EvidencePanel evidence={evidence} />
    </div>
  )
}
