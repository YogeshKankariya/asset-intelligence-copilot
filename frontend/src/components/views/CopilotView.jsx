import ChatWorkspace from '../ChatWorkspace'
import QuestionInput from '../QuestionInput'

export default function CopilotView() {
  return (
    <div className="copilot-view-layout">
      <ChatWorkspace />
      <QuestionInput />
    </div>
  )
}
