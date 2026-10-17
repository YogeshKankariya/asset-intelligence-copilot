import { useEffect, useRef } from 'react'
import { useAssistant } from '../context/useAssistant'
import GenerativeUIRenderer from './GenerativeUIRenderer'

export default function ChatWorkspace() {
  const { messages, sendMessage } = useAssistant()
  const messagesEndRef = useRef(null)

  const starterQuestions = [
    {
      category: 'Production Status',
      icon: '⚡',
      question: 'Is WELL-0001 producing?',
      assetId: 'WELL-0001',
      desc: 'Checks T200 thermal differential (≥15°C above ambient) and latest inspection.',
    },
    {
      category: 'Downtime Estimation',
      icon: '⏱️',
      question: "What was WELL-0001's estimated downtime in 2025?",
      assetId: 'WELL-0001',
      desc: 'Computes downtime at 7 days per weekly non-producing inspection.',
    },
    {
      category: 'Maintenance & RCA',
      icon: '🔧',
      question: 'Does WELL-0001 require a root-cause analysis?',
      assetId: 'WELL-0001',
      desc: 'Audits 12-month window for 3+ corrective maintenance events on same equipment.',
    },
    {
      category: 'Safety & Alarms',
      icon: '🚨',
      question: 'What does the T200 manual require for a high-temperature alarm?',
      assetId: null,
      desc: 'Retrieves Section 9.3 requirement (24-hour wellhead inspection if >85°C).',
    },
    {
      category: 'Spill Reporting',
      icon: '🛢️',
      question: 'What does SOP SR-01 require for a reportable spill?',
      assetId: null,
      desc: 'Verifies 5 bbl notification threshold and 24-hour regulatory filing deadline.',
    },
    {
      category: 'Work Scope Protocols',
      icon: '📋',
      question: 'What are the pressure test requirements under protocol WS-05?',
      assetId: null,
      desc: 'Retrieves testing pressure (1.25 × MOP) and 4-hour stabilization hold period.',
    },
  ]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="chat-workspace">
      {messages.length === 0 ? (
        <div className="welcome-hero">
          <div className="welcome-badge">Operational Intelligence Assistant</div>
          <h3 className="welcome-title">Natural-Language Operational Intelligence</h3>
          <p className="welcome-description">
            Ask questions about well production status, downtime estimation, recurring maintenance,
            and safety compliance. All answers are strictly grounded in physical operating manuals,
            inspections, and maintenance logs.
          </p>

          <div className="starter-grid">
            <span className="starters-header">Suggested Operational Inquiries:</span>
            <div className="starters-list">
              {starterQuestions.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="starter-card"
                  onClick={() => sendMessage(item.question, item.assetId)}
                >
                  <div className="starter-card-header">
                    <span className="starter-icon">{item.icon}</span>
                    <span className="starter-category">{item.category}</span>
                  </div>
                  <strong className="starter-question">{item.question}</strong>
                  <p className="starter-desc">{item.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="messages-stream">
          {messages.map((msg) => (
            <article
              key={msg.id}
              className={`chat-turn ${msg.sender === 'user' ? 'turn-user' : 'turn-assistant'}`}
            >
              <div className="turn-avatar">
                {msg.sender === 'user' ? '👤' : '🤖'}
              </div>

              <div className="turn-bubble-wrapper">
                <div className="turn-meta-header">
                  <span className="turn-author">
                    {msg.sender === 'user' ? 'Operator' : 'Asset Intelligence Copilot'}
                  </span>
                  {msg.asset_id && (
                    <span className="turn-asset-tag">Asset: {msg.asset_id}</span>
                  )}
                  <span className="turn-time">{msg.timestamp}</span>
                </div>

                {msg.sender === 'user' ? (
                  <div className="user-text-bubble">{msg.text}</div>
                ) : (
                  <div className="assistant-content-bubble">
                    <GenerativeUIRenderer message={msg} />
                  </div>
                )}
              </div>
            </article>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  )
}
