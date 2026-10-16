import HelpChat from '@/components/feedback/HelpChat'
import DashboardShell from '@/components/layout/DashboardShell'
import AgreementGate from '@/components/legal/AgreementGate'

export default function TutorLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardShell role="tutor">
      <AgreementGate>
        {children}
        <HelpChat role="tutor" />
      </AgreementGate>
    </DashboardShell>
  )
}
