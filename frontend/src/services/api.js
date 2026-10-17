import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Checks backend health status.
 */
export async function checkBackendHealth() {
  try {
    const res = await apiClient.get('/health')
    return { ok: res.data?.status === 'ok', data: res.data }
  } catch (err) {
    return { ok: false, error: err.message }
  }
}

/**
 * Asks a natural-language question through the assistant endpoint.
 *
 * @param {string} question
 * @param {string | null} assetId
 * @returns {Promise<object>} AssistantAskResponse
 */
export async function askAssistant(question, assetId = null) {
  const payload = {
    question: question.trim(),
    asset_id: assetId && assetId.trim() ? assetId.trim() : null,
  }

  try {
    const res = await apiClient.post('/api/assistant/ask', payload)
    return res.data
  } catch (err) {
    const status = err.response?.status
    const detail = err.response?.data?.detail || err.response?.data?.message

    if (!err.response) {
      throw new Error(
        'Backend connection failed. Please ensure the FastAPI server is running at ' +
          (API_BASE_URL || 'http://127.0.0.1:8000') +
          '.',
        { cause: err }
      )
    }

    if (status === 404) {
      throw new Error(detail || 'The requested well or resource was not found.', { cause: err })
    }

    if (status === 400) {
      throw new Error(detail || 'Invalid asset ID or request format.', { cause: err })
    }

    if (status === 422) {
      throw new Error(detail || 'Validation error or unsupported well type.', { cause: err })
    }

    throw new Error(detail || `Server error (${status}). Please try again.`, { cause: err })
  }
}

/**
 * Lists available wells in the dataset.
 */
export async function listWells() {
  try {
    const res = await apiClient.get('/api/wells')
    return res.data?.wells || []
  } catch (err) {
    console.warn('Failed to load wells list:', err.message)
    return []
  }
}

/**
 * Gets production status for a specific well.
 */
export async function getWellStatus(assetId) {
  const res = await apiClient.get(`/api/wells/${encodeURIComponent(assetId)}/status`)
  return res.data
}

/**
 * Gets downtime metrics for a specific well.
 */
export async function getWellDowntime(assetId, year = null) {
  const params = year ? { year } : {}
  const res = await apiClient.get(`/api/wells/${encodeURIComponent(assetId)}/downtime`, { params })
  return res.data
}

/**
 * Gets safety and compliance events for a specific well.
 */
export async function getWellSafetyCompliance(assetId) {
  const res = await apiClient.get(`/api/wells/${encodeURIComponent(assetId)}/safety-compliance`)
  return res.data
}

/**
 * Gets maintenance recurrence analysis for a specific well.
 */
export async function getWellMaintenanceRecurrence(assetId) {
  const res = await apiClient.get(`/api/wells/${encodeURIComponent(assetId)}/maintenance-recurrence`)
  return res.data
}
