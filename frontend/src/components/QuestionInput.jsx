import { useState, useRef, useEffect } from 'react'
import { useAssistant } from '../context/useAssistant'

export default function QuestionInput() {
  const { sendMessage, isLoading, activeWellId, setActiveWellId } = useAssistant()
  const [questionText, setQuestionText] = useState('')
  const textareaRef = useRef(null)

  // Focus textarea on load
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [])

  const handleSubmit = (e) => {
    if (e) e.preventDefault()
    if (!questionText.trim() || isLoading) return

    sendMessage(questionText, activeWellId)
    setQuestionText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="input-bar-container">
      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-top-bar">
          <div className="asset-scope-control">
            <span className="scope-icon">🎯</span>
            <label htmlFor="well-target-input" className="sr-only">Target Well</label>
            <input
              id="well-target-input"
              type="text"
              className="asset-scope-input"
              placeholder="Asset (e.g. WELL-0001)"
              value={activeWellId || ''}
              onChange={(e) => setActiveWellId(e.target.value.toUpperCase() || null)}
            />
            {activeWellId && (
              <button
                type="button"
                className="clear-scope-small-btn"
                onClick={() => setActiveWellId(null)}
                aria-label="Clear asset scope"
              >
                ×
              </button>
            )}
          </div>
          <span className="shortcut-hint">Press <strong>Enter ↵</strong> to submit · <strong>Shift+Enter</strong> for newline</span>
        </div>

        <div className="input-main-row">
          <textarea
            ref={textareaRef}
            className="question-textarea"
            placeholder={
              activeWellId
                ? `Ask about ${activeWellId} (e.g. Is it producing? What was its 2025 downtime? Any RCA required?)...`
                : 'Ask an operational question (e.g. Is WELL-0001 producing? What does SOP WS-05 require?)...'
            }
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={2}
          />

          <button
            type="submit"
            className="send-button"
            disabled={isLoading || !questionText.trim()}
            aria-label="Send operational query"
          >
            {isLoading ? (
              <span className="send-spinner" aria-hidden="true"></span>
            ) : (
              <span className="send-arrow">➔</span>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
