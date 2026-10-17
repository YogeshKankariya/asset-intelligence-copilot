import ConflictNotice from './ConflictNotice'
import EvidencePanel from './EvidencePanel'
import { parseMarkdown } from '../../utils/markdownParser'

export default function GenericAnswerCard({ data }) {
  const {
    answer,
    rule_or_calculation,
    evidence = [],
    conflicts = [],
    unresolved_conflicts = false,
    details = {},
  } = data

  const isLlmSynthesized = details.llm_synthesized === true
  const llmProvider = details.llm_provider || 'LLM'

  return (
    <div className="generative-card generic-answer-card">
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
