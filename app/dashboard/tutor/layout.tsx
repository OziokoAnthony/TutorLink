import DashboardShell from '@/components/layout/DashboardShell'

export default function TutorLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell role="tutor">{children}</DashboardShell>
}
