import HelpChat from '@/components/feedback/HelpChat'
import DashboardShell from '@/components/layout/DashboardShell'

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardShell role="parent">
      {children}
      <HelpChat role="parent" />
    </DashboardShell>
  )
}
