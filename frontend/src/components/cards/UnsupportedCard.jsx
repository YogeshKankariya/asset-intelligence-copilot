export default function UnsupportedCard({ data }) {
  const { answer } = data

  return (
    <div className="generative-card unsupported-card">
      <div className="card-header">
        <span className="card-badge unsupported-badge">Outside Operational Scope</span>
        <span className="card-subtitle">Domain Boundary</span>
      </div>

      <p className="card-message-text">{answer}</p>

      <div className="supported-scope-summary">
        <span className="scope-title">Supported Operational Topics:</span>
        <ul className="scope-list">
          <li><strong>Production Status:</strong> T200 (ΔT ≥ 15°C) and T350 (ΔT ≥ 20°C) thermal rule validation</li>
          <li><strong>Estimated Downtime:</strong> Weekly non-producing event accounting (7d per weekly inspection)</li>
          <li><strong>Consecutive Downtime:</strong> Multi-week streak monitoring and supervisor notification (&gt;14 days)</li>
          <li><strong>Maintenance Recurrence:</strong> 3+ corrective events in 12 months &amp; RCA triggers</li>
          <li><strong>Safety &amp; Compliance:</strong> High-temp alarms (85°C / 95°C), pad spills (&gt;5%), and SR-01 spills (≥5 bbl)</li>
          <li><strong>Technical Documentation:</strong> T200/T350 manuals, work scope protocols (WS-01..WS-07), SOPs, and maintenance records</li>
        </ul>
      </div>
    </div>
  )
}
