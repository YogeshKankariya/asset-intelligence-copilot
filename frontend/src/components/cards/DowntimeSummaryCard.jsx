import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import EvidencePanel from './EvidencePanel'

export default function DowntimeSummaryCard({ data }) {
  const {
    asset_id,
    details = {},
    evidence = [],
    rule_or_calculation,
  } = data

  const downtimeDays = details.downtime_days ?? (evidence.length * 7)
  const nonProducingCount = details.non_producing_inspections_count ?? evidence.length
  const totalCount = details.total_inspections_in_period
  const period = details.year ? `Year ${details.year}` : 'Recorded Period'

  // Prepare chart data from events or evidence
  const rawEvents = details.events || evidence || []
  const chartData = rawEvents
    .filter((e) => e.timestamp || e.inspected_at)
    .map((e, idx) => {
      const rawDate = e.timestamp || e.inspected_at || `Event ${idx + 1}`
      const dateStr = rawDate.length >= 10 ? rawDate.substring(0, 10) : rawDate
      return {
        date: dateStr,
        downtime: e.downtime_days ?? 7,
        id: e.inspection_id || `INS-${idx + 1}`,
        tempDiff: e.temp_diff_c ?? e.temperature_difference_c ?? 0,
      }
    })
    .sort((a, b) => (a.date > b.date ? 1 : -1))

  return (
    <div className="generative-card downtime-card">
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge asset-badge">{asset_id || 'WELL'}</span>
          <span className="card-badge period-badge">{period}</span>
          <span className="card-subtitle">Estimated Operational Downtime</span>
        </div>
        <div className="status-pill status-downtime">
          {downtimeDays} DAYS ESTIMATED
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric-box hero-metric">
          <span className="metric-label">Estimated Downtime</span>
          <span className="metric-number">{downtimeDays}</span>
          <span className="metric-unit">Days</span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Non-Producing Inspections</span>
          <span className="metric-number text-amber">{nonProducingCount}</span>
          <span className="metric-subtext">Events contributing 7d each</span>
        </div>

        {totalCount !== undefined && (
          <div className="metric-box">
            <span className="metric-label">Total Period Inspections</span>
            <span className="metric-number">{totalCount}</span>
            <span className="metric-subtext">
              Availability: {Math.max(0, Math.round(((totalCount - nonProducingCount) / totalCount) * 100))}%
            </span>
          </div>
        )}
      </div>

      {/* Chart visualization when events exist */}
      {chartData.length > 0 && (
        <div className="chart-section">
          <div className="chart-title-row">
            <span className="chart-title">Non-Producing Inspection Events Contributing Downtime</span>
            <span className="chart-legend-tag">7 Days per Event</span>
          </div>
          <div className="chart-container" style={{ width: '100%', height: 180 }}>
            <ResponsiveContainer>
              <BarChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 10]} ticks={[0, 7, 10]} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload
                      return (
                        <div className="custom-tooltip">
                          <p className="tooltip-title">{d.id} ({d.date})</p>
                          <p className="tooltip-value">Downtime Contributed: {d.downtime} days</p>
                          <p className="tooltip-sub">Thermal Delta: {d.tempDiff}°C</p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="downtime" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Accounting Rule:</strong> {rule_or_calculation}
        </div>
      )}

      <div className="card-disclaimer">
        ℹ️ <strong>Standard Accounting Principle:</strong> Downtime is estimated at 7 days per non-producing weekly
        inspection. Missed inspection weeks do not add downtime. This differs from continuous sensor telemetry.
      </div>

      <EvidencePanel evidence={evidence} />
    </div>
  )
}
