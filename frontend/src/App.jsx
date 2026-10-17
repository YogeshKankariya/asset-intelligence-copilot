import { useState } from 'react'
import { AssistantProvider } from './context/AssistantContext'
import { useAssistant } from './context/useAssistant'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import CopilotView from './components/views/CopilotView'
import WellOperationsView from './components/views/WellOperationsView'
import EvidenceActivityView from './components/views/EvidenceActivityView'
import './App.css'

function AppContent() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const { currentView } = useAssistant()

  return (
    <div className="app-container">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className="app-main-wrapper">
        <Header onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />
        <main className="app-view-container" id="main-content">
          {currentView === 'copilot' && <CopilotView />}
          {currentView === 'operations' && <WellOperationsView />}
          {currentView === 'evidence' && <EvidenceActivityView />}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AssistantProvider>
      <AppContent />
    </AssistantProvider>
  )
}
