import ConflictNotice from './ConflictNotice'
import EvidencePanel from './EvidencePanel'
import { parseMarkdown } from '../../utils/markdownParser'

export default function RepairTypesCard({ data }) {
  const {
    asset_id,
    answer,
    rule_or_calculation,
    evidence = [],
    conflicts = [],
    unresolved_conflicts = false,
    details = {},
  } = data

  const isLlmSynthesized = details.llm_synthesized === true
  const llmProvider = details.llm_provider || 'LLM'

  const scope = details.scope || (asset_id ? 'asset' : 'fleet')
  const totalRecords = details.total_records ?? 0
  const correctiveCount = details.corrective_count ?? details.maintenance_types?.corrective ?? 0
  const scheduledCount = details.scheduled_count ?? details.maintenance_types?.scheduled ?? 0
  const subsystemCount = details.corrective_equipment_kind_count ?? Object.keys(details.corrective_equipment_kinds || {}).length

  return (
    <div className="generative-card repair-types-card">
      <div className="card-header-row">
        <div className="card-title-group">
          <span className="card-type-icon" aria-hidden="true">🔧</span>
          <div>
            <h3 className="card-title">Maintenance &amp; Repair Types</h3>
            <span className="card-subtitle">
              {scope === 'asset' && asset_id
                ? `Operational breakdown for ${asset_id}`
                : 'Fleet-wide operational classification'}
            </span>
          </div>
        </div>

        <div className="scope-badge">
          {scope === 'asset' && asset_id ? asset_id : 'Fleet-Wide'}
        </div>
      </div>

      {isLlmSynthesized && (
        <div className="synthesis-badge-row">
          <span className="synthesis-badge">
            ✨ Grounded Synthesis ({llmProvider})
          </span>
          <span className="synthesis-provenance-note">
            Citations verified against retrieved evidence
          </span>
        </div>
      )}

      {/* High-level KPI Stats */}
      <div className="metrics-grid">
        <div className="metric-box">
          <span className="metric-label">Total Maintenance</span>
          <span className="metric-val">{totalRecords.toLocaleString()}</span>
          <span className="metric-unit">events logged</span>
        </div>

        <div className="metric-box status-active">
          <span className="metric-label">Corrective Repairs</span>
          <span className="metric-val">{correctiveCount.toLocaleString()}</span>
          <span className="metric-unit">
            {totalRecords > 0 ? `${((correctiveCount / totalRecords) * 100).toFixed(1)}%` : '0%'} of total
          </span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Scheduled (Preventive)</span>
          <span className="metric-val">{scheduledCount.toLocaleString()}</span>
          <span className="metric-unit">
            {totalRecords > 0 ? `${((scheduledCount / totalRecords) * 100).toFixed(1)}%` : '0%'} of total
          </span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Subsystems Repaired</span>
          <span className="metric-val">{subsystemCount}</span>
          <span className="metric-unit">distinct equipment kinds</span>
        </div>
      </div>

      {/* Structured Answer Prose with Safe Markdown */}
      <div className="answer-prose">
        {parseMarkdown(answer)}
      </div>

      {rule_or_calculation && (
        <div className="applied-rule-banner">
          <strong>Applied Method:</strong> {rule_or_calculation}
        </div>
      )}

      <ConflictNotice conflicts={conflicts} unresolvedConflicts={unresolved_conflicts} />
      <EvidencePanel evidence={evidence} />
    </div>
  )
}
