import { useState } from 'react'
import { useAssistant } from '../../context/useAssistant'
import EvidencePanel from '../cards/EvidencePanel'

export default function EvidenceActivityView() {
  const { messages } = useAssistant()
  const [searchTerm, setSearchTerm] = useState('')

  // Aggregate all evidence cited in assistant messages
  const allEvidence = []
  const allConflicts = []

  messages.forEach((msg) => {
    if (msg.sender === 'assistant') {
      if (msg.evidence && Array.isArray(msg.evidence)) {
        msg.evidence.forEach((item) => {
          allEvidence.push({
            ...item,
            queryQuestion: msg.question,
            queryTime: msg.timestamp,
          })
        })
      }
      if (msg.conflicts && Array.isArray(msg.conflicts)) {
        msg.conflicts.forEach((c) => {
          allConflicts.push({
            ...c,
            queryQuestion: msg.question,
          })
        })
      }
    }
  })

  // Filter by search term
  const filteredEvidence = allEvidence.filter((item) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    const str = `${item.source || ''} ${item.record_id || ''} ${item.document_title || ''} ${item.section || ''} ${item.excerpt || ''}`.toLowerCase()
    return str.includes(term)
  })

  return (
    <div className="evidence-activity-layout">
      <div className="activity-header-bar">
        <div>
          <h3 className="activity-title">Session Evidence &amp; Citation Registry</h3>
          <p className="activity-subtitle">
            Catalog of all verified records, manual passages, and protocol excerpts retrieved during this session.
          </p>
        </div>
        <div className="activity-search-box">
          <input
            type="text"
            className="activity-search-input"
            placeholder="Search cited records (e.g. WS-05, MNT, INS)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {allConflicts.length > 0 && (
        <div className="session-conflicts-container">
          <h4 className="section-title">Disclosed Discrepancies &amp; Conflicts ({allConflicts.length})</h4>
          <div className="conflicts-grid">
            {allConflicts.map((c, idx) => (
              <div key={idx} className="conflict-card-mini">
                <div className="conflict-mini-header">
                  <span className="mini-icon">⚠️</span>
                  <strong>{c.field || 'Record field'}</strong>
                  <span className={`pill-tag ${c.is_resolved ? 'resolved' : 'unresolved'}`}>
                    {c.is_resolved ? 'Resolved' : 'Unresolved'}
                  </span>
                </div>
                <p className="mini-desc">{c.description}</p>
                {c.resolution && <p className="mini-res">Rule: {c.resolution}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="session-evidence-container">
        <div className="evidence-count-header">
          <span>Cited Evidence Items ({filteredEvidence.length})</span>
          {searchTerm && <span>Filtered by &quot;{searchTerm}&quot;</span>}
        </div>

        {filteredEvidence.length === 0 ? (
          <div className="empty-evidence-placeholder">
            {allEvidence.length === 0 ? (
              <p>No evidence has been retrieved yet. Ask a question in Copilot to inspect verified evidence.</p>
            ) : (
              <p>No evidence items matched &quot;{searchTerm}&quot;.</p>
            )}
          </div>
        ) : (
          <div className="evidence-cards-list">
            <EvidencePanel evidence={filteredEvidence} />
          </div>
        )}
      </div>
    </div>
  )
}
