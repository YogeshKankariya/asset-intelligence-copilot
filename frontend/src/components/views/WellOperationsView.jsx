import { useState, useEffect } from 'react'
import { useAssistant } from '../../context/useAssistant'
import {
  getWellStatus,
  getWellDowntime,
  getWellSafetyCompliance,
  getWellMaintenanceRecurrence,
} from '../../services/api'
import ProductionStatusCard from '../cards/ProductionStatusCard'
import DowntimeSummaryCard from '../cards/DowntimeSummaryCard'
import SafetyCompliancePanel from '../cards/SafetyCompliancePanel'
import MaintenanceRecurrenceCard from '../cards/MaintenanceRecurrenceCard'

export default function WellOperationsView() {
  const { wells, activeWellId, setActiveWellId, setCurrentView, sendMessage } = useAssistant()
  const [selectedWell, setSelectedWell] = useState(activeWellId || 'WELL-0001')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [statusData, setStatusData] = useState(null)
  const [downtimeData, setDowntimeData] = useState(null)
  const [safetyData, setSafetyData] = useState(null)
  const [maintenanceData, setMaintenanceData] = useState(null)

  useEffect(() => {
    let mounted = true
    async function loadWellData(wellId) {
      if (!wellId) return
      setLoading(true)
      setError(null)

      try {
        const [status, downtime, safety, maintenance] = await Promise.allSettled([
          getWellStatus(wellId),
          getWellDowntime(wellId, 2025),
          getWellSafetyCompliance(wellId),
          getWellMaintenanceRecurrence(wellId),
        ])

        if (!mounted) return

        if (status.status === 'fulfilled') {
          setStatusData({
            asset_id: wellId,
            question_type: 'production_status',
            details: status.value,
            evidence: status.value.evidence || [],
            conflicts: status.value.conflicts || [],
            unresolved_conflicts: status.value.conflict_status === 'unresolved',
            rule_or_calculation: `${status.value.well_type} threshold: ΔT ≥ ${status.value.threshold_c}°C`,
          })
        }

        if (downtime.status === 'fulfilled') {
          setDowntimeData({
            asset_id: wellId,
            question_type: 'downtime',
            details: downtime.value,
            evidence: downtime.value.evidence || [],
            rule_or_calculation: downtime.value.explanation,
          })
        }

        if (safety.status === 'fulfilled') {
          setSafetyData({
            asset_id: wellId,
            question_type: 'safety_compliance',
            details: safety.value,
            evidence: safety.value.evidence || [],
            rule_or_calculation: safety.value.explanation,
          })
        }

        if (maintenance.status === 'fulfilled') {
          setMaintenanceData({
            asset_id: wellId,
            question_type: 'maintenance_recurrence',
            details: maintenance.value,
            evidence: maintenance.value.evidence || [],
            rule_or_calculation: maintenance.value.explanation,
          })
        }
      } catch (err) {
        if (mounted) setError(err.message)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadWellData(selectedWell)
    return () => {
      mounted = false
    }
  }, [selectedWell])

  const handleSelectWell = (wellId) => {
    setSelectedWell(wellId)
    setActiveWellId(wellId)
  }

  const handleAskCopilot = (promptText) => {
    setActiveWellId(selectedWell)
    setCurrentView('copilot')
    sendMessage(promptText, selectedWell)
  }

  return (
    <div className="operations-view-layout">
      {/* Top Selector Bar */}
      <div className="operations-top-bar">
        <div className="operations-selector-group">
          <label htmlFor="well-operations-select" className="selector-label">
            Select Asset:
          </label>
          <select
            id="well-operations-select"
            className="operations-well-select"
            value={selectedWell}
            onChange={(e) => handleSelectWell(e.target.value)}
          >
            {wells.map((w) => (
              <option key={w.asset_id} value={w.asset_id}>
                {w.asset_id} — {w.well_type || 'Unknown'} {w.name ? `(${w.name})` : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="operations-quick-actions">
          <button
            type="button"
            className="action-btn"
            onClick={() => handleAskCopilot(`Is ${selectedWell} producing?`)}
          >
            💬 Check Production
          </button>
          <button
            type="button"
            className="action-btn"
            onClick={() => handleAskCopilot(`What was ${selectedWell}'s downtime in 2025?`)}
          >
            ⏱️ Check 2025 Downtime
          </button>
          <button
            type="button"
            className="action-btn"
            onClick={() => handleAskCopilot(`Check safety and spills for ${selectedWell}`)}
          >
            🚨 Audit Safety
          </button>
        </div>
      </div>

      {loading ? (
        <div className="operations-loading">
          <div className="pulse-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <p>Querying verified operational records for {selectedWell}...</p>
        </div>
      ) : error ? (
        <div className="error-card">
          <p>Failed to load operational data for {selectedWell}: {error}</p>
        </div>
      ) : (
        <div className="operations-dashboard-grid">
          {statusData && (
            <div className="dashboard-cell">
              <h3 className="cell-header">Current Physical Production Status</h3>
              <ProductionStatusCard data={statusData} />
            </div>
          )}

          {downtimeData && (
            <div className="dashboard-cell">
              <h3 className="cell-header">2025 Estimated Downtime Accounting</h3>
              <DowntimeSummaryCard data={downtimeData} />
            </div>
          )}

          {safetyData && (
            <div className="dashboard-cell">
              <h3 className="cell-header">Safety &amp; Spill Compliance Audit</h3>
              <SafetyCompliancePanel data={safetyData} />
            </div>
          )}

          {maintenanceData && (
            <div className="dashboard-cell">
              <h3 className="cell-header">Maintenance Recurrence &amp; RCA Triggers</h3>
              <MaintenanceRecurrenceCard data={maintenanceData} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
