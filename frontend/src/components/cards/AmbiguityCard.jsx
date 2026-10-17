import { useAssistant } from '../../context/useAssistant'

export default function AmbiguityCard({ data }) {
  const { sendMessage } = useAssistant()
  const { answer, asset_id } = data
  const targetWell = asset_id || 'WELL-0001'

  const focusedOptions = [
    { label: 'Current Production Status', query: `Is ${targetWell} producing?` },
    { label: 'Estimated Downtime (2025)', query: `What was ${targetWell}'s estimated downtime in 2025?` },
    { label: 'Consecutive Downtime (>14d)', query: `Check consecutive downtime for ${targetWell}` },
    { label: 'Maintenance Recurrence / RCA', query: `Does ${targetWell} require a root-cause analysis?` },
    { label: 'Safety & Environmental Alerts', query: `Check safety alarms and spills for ${targetWell}` },
  ]

  return (
    <div className="generative-card ambiguity-card">
      <div className="card-header">
        <span className="card-badge ambiguity-badge">Ambiguous Query</span>
        <span className="card-subtitle">Multiple Operational Domains</span>
      </div>

      <p className="card-message-text">{answer}</p>

      <div className="ambiguity-options">
        <span className="suggestions-label">Choose one focused inquiry:</span>
        <div className="focused-chips-grid">
          {focusedOptions.map((opt, idx) => (
            <button
              key={idx}
              type="button"
              className="focused-chip"
              onClick={() => sendMessage(opt.query, targetWell)}
            >
              <span className="chip-bullet">👉</span>
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
