import { useState, useEffect, useCallback } from 'react'
import {
  askAssistant,
  checkBackendHealth,
  listWells,
} from '../services/api'
import { AssistantContext } from './assistantContextDefinition'

export function AssistantProvider({ children }) {
  const [messages, setMessages] = useState([])
  const [activeWellId, setActiveWellId] = useState(null)
  const [currentView, setCurrentView] = useState('copilot') // 'copilot' | 'operations' | 'evidence'
  const [isLoading, setIsLoading] = useState(false)
  const [backendHealthy, setBackendHealthy] = useState(null)
  const [wells, setWells] = useState([])
  const [lastFailedRequest, setLastFailedRequest] = useState(null)

  // Initialize backend health check and well list
  useEffect(() => {
    let mounted = true

    async function init() {
      const health = await checkBackendHealth()
      if (mounted) setBackendHealthy(health.ok)

      const wellList = await listWells()
      if (mounted && wellList.length > 0) {
        setWells(wellList)
      }
    }

    init()
    const interval = setInterval(async () => {
      const health = await checkBackendHealth()
      if (mounted) setBackendHealthy(health.ok)
    }, 30000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const sendMessage = useCallback(
    async (questionText, explicitAssetId = null) => {
      if (!questionText || !questionText.trim()) return

      const q = questionText.trim()
      const aid = explicitAssetId || activeWellId

      const userMsgId = 'user-' + Date.now()
      const assistantMsgId = 'asst-' + (Date.now() + 1)

      const userMessage = {
        id: userMsgId,
        sender: 'user',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: q,
        asset_id: aid,
      }

      const pendingAssistantMessage = {
        id: assistantMsgId,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        question: q,
        asset_id: aid,
        isPending: true,
      }

      setMessages((prev) => [...prev, userMessage, pendingAssistantMessage])
      setIsLoading(true)
      setLastFailedRequest(null)

      try {
        const responseData = await askAssistant(q, aid)

        // Update active well if extracted by assistant
        if (responseData.asset_id && !activeWellId) {
          setActiveWellId(responseData.asset_id)
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  isPending: false,
                  status: responseData.status,
                  question_type: responseData.question_type,
                  answer: responseData.answer,
                  rule_or_calculation: responseData.rule_or_calculation,
                  evidence: responseData.evidence || [],
                  conflicts: responseData.conflicts || [],
                  unresolved_conflicts: responseData.unresolved_conflicts || false,
                  details: responseData.details || {},
                  asset_id: responseData.asset_id || aid,
                }
              : msg
          )
        )
      } catch (err) {
        setLastFailedRequest({ question: q, assetId: aid })
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  isPending: false,
                  status: 'error',
                  error: err.message,
                  answer: 'Error: ' + err.message,
                }
              : msg
          )
        )
      } finally {
        setIsLoading(false)
      }
    },
    [activeWellId]
  )

  const retryLastMessage = useCallback(() => {
    if (!lastFailedRequest) return
    sendMessage(lastFailedRequest.question, lastFailedRequest.assetId)
  }, [lastFailedRequest, sendMessage])

  const clearMessages = useCallback(() => {
    setMessages([])
    setLastFailedRequest(null)
  }, [])

  return (
    <AssistantContext.Provider
      value={{
        messages,
        activeWellId,
        setActiveWellId,
        currentView,
        setCurrentView,
        isLoading,
        backendHealthy,
        wells,
        sendMessage,
        retryLastMessage,
        clearMessages,
      }}
    >
      {children}
    </AssistantContext.Provider>
  )
}
