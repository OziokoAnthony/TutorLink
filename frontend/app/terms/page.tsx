import type { Metadata } from 'next'
import Link from 'next/link'
import LegalPage from '@/components/legal/LegalPage'
import { detail } from '@/lib/legal'

export const metadata: Metadata = { title: 'Terms of service · TutorLink' }

/** The rules of using TutorLink, following specs 1-4 and 6. */
export default function TermsPage() {
  return (
    <LegalPage title="Terms of service">
      <p>
        These terms are an agreement between you and {detail('company')}, {detail('address')} (&quot;TutorLink&quot;),
        for using TutorLink. By creating an account you accept them and our{' '}
        <Link href="/privacy" className="text-primary hover:underline">privacy notice</Link>.
      </p>

      <h2>1. What TutorLink does</h2>
      <p>
        TutorLink connects parents with tutors for lessons at home or online, takes payment before lessons and pays
        tutors after them. Tutors are independent: they aren&apos;t TutorLink&apos;s employees, and each tutor is
        responsible for the lessons they give.
      </p>

      <h2>2. Your account</h2>
      <ul>
        <li>You must be 18 or over, and give true details. Tutors must register in their name exactly as on their NIN
          record.</li>
        <li>Keep your password private. You&apos;re responsible for what happens in your account.</li>
        <li>We may suspend an account that breaks these terms, puts a child at risk or is used for fraud.</li>
      </ul>

      <h2>3. Tutors</h2>
      <ul>
        <li>Before parents can see you, you must verify your NIN, have a certificate verified by us, pass the
          qualifying quiz and be approved. We may refuse or withdraw approval.</li>
        <li>Answer booking requests within 72 hours, turn up to every paid lesson, and submit each lesson&apos;s report
          within 24 hours. Online lessons need their recording uploaded before the report.</li>
        <li>An earning becomes payable 24 hours after your report if the parent reports no problem, and is paid to your
          bank account 48 hours after the last lesson of its billing period. TutorLink&apos;s fee is deducted from
          the lesson price, and your dashboard shows exactly what you&apos;ll receive.</li>
      </ul>

      <h2>4. Parents: booking and paying</h2>
      <ul>
        <li>You pay by bank transfer into your own TutorLink account number. We don&apos;t take cards. The price you see
          includes TutorLink&apos;s fee, and you always see the full amount before paying.</li>
        <li>Money you send becomes your TutorLink balance, which pays due billing periods automatically, oldest first.</li>
        <li>The first period must be paid at least 24 hours before its first lesson, or the booking is released. Each
          later period must be paid 24 hours before its first lesson, or the booking pauses; a booking paused for 7 days
          ends.</li>
        <li>You can withdraw your balance to your bank account. We process withdrawals by hand.</li>
      </ul>

      <h2>5. Cancelling, problems and refunds</h2>
      <ul>
        <li>If you cancel with at least 48 hours&apos; notice before a paid lesson, lessons 48 or more hours away are
          refunded to your balance once we approve it. The refund is the lesson price, not TutorLink&apos;s fee. Lessons
          sooner than that go ahead as normal.</li>
        <li>If something goes wrong with a lesson (the tutor didn&apos;t come, came late or left early, or broke what was
          agreed), report it from the lesson, until 24 hours after the tutor&apos;s report. We then refund the lesson to
          your balance, reschedule it, or let it stand.</li>
      </ul>

      <h2>6. Recordings</h2>
      <p>
        Online lessons are recorded so problems can be reviewed. Only the parent, the tutor and TutorLink can watch a
        recording, and it&apos;s deleted 90 days after the lesson unless a problem on it is still open. Don&apos;t copy
        or share recordings.
      </p>

      <h2>7. Behaving well</h2>
      <ul>
        <li>Treat each other with respect, and keep children safe at all times.</li>
        <li>Don&apos;t post anything false, offensive or unlawful, or use someone else&apos;s identity or documents.</li>
        <li>Don&apos;t try to break, overload or get around the security of TutorLink.</li>
      </ul>

      <h2>8. Help assistant</h2>
      <p>
        The help chat&apos;s answers come from an AI assistant and may be wrong. They don&apos;t change these terms or
        your bookings. For anything about your own account, send the conversation to our team.
      </p>

      <h2>9. Our responsibility</h2>
      <p>
        We vet tutors carefully, but we can&apos;t guarantee a child&apos;s results. As far as the law allows, we&apos;re
        not liable for indirect losses, and our liability for any booking is limited to what you paid TutorLink for
        it. Nothing in these terms takes away rights you have under Nigerian consumer law.
      </p>

      <h2>10. Changes and the law</h2>
      <p>
        If we change these terms, we&apos;ll tell you in the app before the change takes effect. These terms are
        governed by the laws of the Federal Republic of Nigeria. Questions: <strong>{detail('email')}</strong>.
      </p>
    </LegalPage>
  )
}
