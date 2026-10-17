import { Component } from 'react'
import ProductionStatusCard from './cards/ProductionStatusCard'
import DowntimeSummaryCard from './cards/DowntimeSummaryCard'
import ConsecutiveDowntimeCard from './cards/ConsecutiveDowntimeCard'
import MaintenanceRecurrenceCard from './cards/MaintenanceRecurrenceCard'
import SafetyCompliancePanel from './cards/SafetyCompliancePanel'
import ClarificationCard from './cards/ClarificationCard'
import AmbiguityCard from './cards/AmbiguityCard'
import UnsupportedCard from './cards/UnsupportedCard'
import GenericAnswerCard from './cards/GenericAnswerCard'
import RepairTypesCard from './cards/RepairTypesCard'
import { useAssistant } from '../context/useAssistant'

class CardErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.warn('Generative UI card render error caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <GenericAnswerCard
          data={{
            answer: this.props.fallbackData?.answer || 'Operational result received.',
            rule_or_calculation: this.props.fallbackData?.rule_or_calculation,
            evidence: this.props.fallbackData?.evidence || [],
            conflicts: this.props.fallbackData?.conflicts || [],
          }}
        />
      )
    }
    return this.props.children
  }
}

export default function GenerativeUIRenderer({ message }) {
  const { retryLastMessage } = useAssistant()

  if (!message) return null

  // 1. Pending / Analyzing State
  if (message.isPending) {
    return (
      <div className="pending-indicator">
        <div className="pulse-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span className="pending-text">
          Evaluating operational records &amp; physical rules...
        </span>
      </div>
    )
  }

  // 2. Error State
  if (message.status === 'error') {
    return (
      <div className="error-card" role="alert">
        <div className="error-header">
          <span className="error-icon">❌</span>
          <strong>Request Failed</strong>
        </div>
        <p className="error-message">{message.error || message.answer}</p>
        <button
          type="button"
          className="retry-button"
          onClick={retryLastMessage}
        >
          🔄 Retry Request
        </button>
      </div>
    )
  }

  // 3. Ambiguity & Clarification States
  if (message.status === 'clarification_needed') {
    return (
      <CardErrorBoundary fallbackData={message}>
        <ClarificationCard data={message} />
      </CardErrorBoundary>
    )
  }

  if (message.status === 'ambiguous') {
    return (
      <CardErrorBoundary fallbackData={message}>
        <AmbiguityCard data={message} />
      </CardErrorBoundary>
    )
  }

  if (message.status === 'unsupported') {
    return (
      <CardErrorBoundary fallbackData={message}>
        <UnsupportedCard data={message} />
      </CardErrorBoundary>
    )
  }

  // 4. Answered States by Question Type
  return (
    <CardErrorBoundary fallbackData={message}>
      {(() => {
        switch (message.question_type) {
          case 'production_status':
            return <ProductionStatusCard data={message} />

          case 'downtime':
            return <DowntimeSummaryCard data={message} />

          case 'consecutive_downtime':
            return <ConsecutiveDowntimeCard data={message} />

          case 'maintenance_recurrence':
            return <MaintenanceRecurrenceCard data={message} />

          case 'safety_compliance':
            return <SafetyCompliancePanel data={message} />

          case 'repair_types':
            return <RepairTypesCard data={message} />

          case 'document_retrieval':
          default:
            return <GenericAnswerCard data={message} />
        }
      })()}
    </CardErrorBoundary>
  )
}
