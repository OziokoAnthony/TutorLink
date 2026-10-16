import RemovalNoticeBanner from '@/components/account/RemovalNoticeBanner'
import HelpChat from '@/components/feedback/HelpChat'
import DashboardShell from '@/components/layout/DashboardShell'
import AgreementGate from '@/components/legal/AgreementGate'

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardShell role="parent">
      <RemovalNoticeBanner />
      <AgreementGate>
        {children}
        <HelpChat role="parent" />
      </AgreementGate>
    </DashboardShell>
  )
}
