import { useState } from 'react'

export default function EvidencePanel({ evidence = [] }) {
  const [isOpen, setIsOpen] = useState(false)

  if (!evidence || evidence.length === 0) return null

  return (
    <div className="evidence-panel">
      <button
        type="button"
        className="evidence-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="evidence-btn-title">
          <span className="evidence-icon">📋</span> Verified Supporting Evidence ({evidence.length})
        </span>
        <span className="evidence-chevron">{isOpen ? '▲ Collapse' : '▼ Expand'}</span>
      </button>

      {isOpen && (
        <div className="evidence-content-list">
          {evidence.map((item, idx) => {
            const src = item.source || item.source_path || item.source_file || 'Dataset record'
            const recId =
              item.record_id ||
              item.inspection_id ||
              item.maintenance_id ||
              item.event_id ||
              item.note_id
            const title = item.document_title || item.section || item.event_type || null
            const timestamp = item.timestamp || item.inspected_at || item.date || null
            const excerpt = item.excerpt || item.content || item.text || null

            return (
              <div key={idx} className="evidence-item-card">
                <div className="evidence-item-meta">
                  <span className="evidence-item-index">#{idx + 1}</span>
                  {recId && <span className="evidence-record-badge">{recId}</span>}
                  {title && <span className="evidence-section-name">{title}</span>}
                  {item.doc_type && <span className="evidence-doctype-tag">{item.doc_type}</span>}
                </div>

                <div className="evidence-source-path">
                  <code>{src}</code>
                  {timestamp && <span className="evidence-timestamp">{timestamp}</span>}
                </div>

                {excerpt && (
                  <blockquote className="evidence-excerpt">
                    {excerpt}
                  </blockquote>
                )}

                {item.wellhead_temp_c !== undefined && item.ambient_temp_c !== undefined && (
                  <div className="evidence-telemetry-row">
                    <span>Wellhead: <strong>{item.wellhead_temp_c}°C</strong></span>
                    <span>Ambient: <strong>{item.ambient_temp_c}°C</strong></span>
                    {item.temperature_difference_c !== undefined && (
                      <span>Delta: <strong>{item.temperature_difference_c}°C</strong></span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
