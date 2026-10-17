import { useAssistant } from '../../context/useAssistant'

export default function ClarificationCard({ data }) {
  const { sendMessage, wells } = useAssistant()
  const { answer, question } = data

  const suggestedWells = wells.length > 0
    ? wells.slice(0, 4).map((w) => w.asset_id)
    : ['WELL-0001', 'WELL-0002', 'WELL-0121']

  const handleSelectWell = (wellId) => {
    // Re-ask the question with the chosen well ID
    sendMessage(question, wellId)
  }

  return (
    <div className="generative-card clarification-card">
      <div className="card-header">
        <span className="card-badge clarification-badge">Clarification Needed</span>
        <span className="card-subtitle">Asset Context Required</span>
      </div>

      <p className="card-message-text">{answer}</p>

      <div className="clarification-suggestions">
        <span className="suggestions-label">Select a well to proceed:</span>
        <div className="suggestion-chips">
          {suggestedWells.map((wid) => (
            <button
              key={wid}
              type="button"
              className="suggestion-chip"
              onClick={() => handleSelectWell(wid)}
            >
              🏷️ {wid}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
