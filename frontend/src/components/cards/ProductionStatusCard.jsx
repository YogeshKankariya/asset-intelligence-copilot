import ConflictNotice from './ConflictNotice'
import EvidencePanel from './EvidencePanel'

export default function ProductionStatusCard({ data }) {
  const {
    asset_id,
    details = {},
    evidence = [],
    conflicts = [],
    unresolved_conflicts = false,
    rule_or_calculation,
  } = data

  const wellType = details.well_type || 'Unknown Type'
  const isProducing = details.computed_status === 'producing'
  const wellhead = details.wellhead_temp_c
  const ambient = details.ambient_temp_c
  const diff = details.temperature_difference_c
  const threshold = details.threshold_c ?? (wellType === 'T350' ? 20.0 : 15.0)
  const timestamp = details.inspection_timestamp || (evidence[0]?.inspected_at)

  // Calculate percentage of threshold achieved for visual gauge
  const progressPct = diff !== undefined && threshold > 0
    ? Math.min(Math.max((diff / threshold) * 100, 0), 150)
    : 0

  return (
    <div className={`generative-card production-card ${isProducing ? 'producing' : 'not-producing'}`}>
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge asset-badge">{asset_id || 'WELL'}</span>
          <span className="card-badge type-badge">{wellType} Well</span>
          <span className="card-subtitle">Production Operational Status</span>
        </div>
        <div className={`status-pill ${isProducing ? 'status-producing' : 'status-not-producing'}`}>
          <span className="status-dot"></span>
          {isProducing ? 'PRODUCING' : 'NOT PRODUCING'}
        </div>
      </div>

      <div className="telemetry-grid">
        <div className="telemetry-cell">
          <span className="telemetry-label">Wellhead Temperature</span>
          <span className="telemetry-value">
            {wellhead !== undefined ? `${wellhead}°C` : 'N/A'}
          </span>
        </div>
        <div className="telemetry-cell">
          <span className="telemetry-label">Ambient Air Temperature</span>
          <span className="telemetry-value">
            {ambient !== undefined ? `${ambient}°C` : 'N/A'}
          </span>
        </div>
        <div className="telemetry-cell highlight-cell">
          <span className="telemetry-label">Thermal Difference (ΔT)</span>
          <span className={`telemetry-value ${diff >= threshold ? 'text-producing' : 'text-not-producing'}`}>
            {diff !== undefined ? `${diff >= 0 ? '+' : ''}${diff}°C` : 'N/A'}
          </span>
          <span className="telemetry-subtext">
            Required: ≥ {threshold}°C ({wellType} manual)
          </span>
        </div>
      </div>

      {/* Visual threshold comparison bar */}
      {diff !== undefined && (
        <div className="gauge-container">
          <div className="gauge-header">
            <span>Thermal Delta vs Threshold</span>
            <span>{diff}°C / {threshold}°C ({Math.round(progressPct)}%)</span>
          </div>
          <div className="gauge-track">
            <div
              className={`gauge-fill ${isProducing ? 'fill-producing' : 'fill-not-producing'}`}
              style={{ width: `${Math.min(progressPct, 100)}%` }}
            ></div>
            <div className="gauge-threshold-line" title={`Threshold: ${threshold}°C`}></div>
          </div>
          <div className="gauge-footer">
            <span>0°C</span>
            <span className="gauge-threshold-label">Threshold: {threshold}°C</span>
            <span>{threshold * 1.5}°C+</span>
          </div>
        </div>
      )}

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Rule Applied:</strong> {rule_or_calculation}
        </div>
      )}

      <ConflictNotice conflicts={conflicts} unresolvedConflicts={unresolved_conflicts} />

      <div className="card-disclaimer">
        ℹ️ <strong>Operational Caveat:</strong> Inferred from latest valid inspection
        {timestamp ? ` (${timestamp})` : ''}. Does not guarantee the well&apos;s current physical state.
      </div>

      <EvidencePanel evidence={evidence} />
    </div>
  )
}
