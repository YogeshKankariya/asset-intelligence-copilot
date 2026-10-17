import { useContext } from 'react'
import { AssistantContext } from './assistantContextDefinition'

export function useAssistant() {
  const ctx = useContext(AssistantContext)
  if (!ctx) {
    throw new Error('useAssistant must be used within an AssistantProvider')
  }
  return ctx
}
