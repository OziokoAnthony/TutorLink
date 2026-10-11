import type { Metadata } from 'next'
import LegalPage from '@/components/legal/LegalPage'
import { detail } from '@/lib/legal'

export const metadata: Metadata = { title: 'Privacy notice · TutorLink' }

/** What TutorLink collects, why, who else handles it and how long it's kept (Nigeria Data Protection Act 2023). */
export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy notice">
      <p>
        TutorLink is run by {detail('company')}, {detail('address')} (&quot;TutorLink&quot;, &quot;we&quot;). We decide how
        your personal data is used, and this notice explains it under the Nigeria Data Protection Act 2023. Questions
        or requests: <strong>{detail('email')}</strong>.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>Everyone:</strong> name, email, phone (if given), password (stored only as a one-way hash) or your
          Google sign-in, profile picture, notifications, and any feedback or help chats you send to our team.</li>
        <li><strong>Parents:</strong> home address (if given), your child&apos;s strengths and weaknesses as you describe
          them in bookings and job posts, bookings, payments into your TutorLink account number, your balance,
          withdrawals and the bank account you withdraw to, problem reports and reviews.</li>
        <li><strong>Tutors:</strong> the areas you cover, your offers and availability, your bio, certificates and their
          details, quiz results, lesson reports, earnings and your payout bank account.</li>
        <li><strong>NIN checks (tutors):</strong> you give your NIN and take a selfie, which we send to our verification
          provider. We keep only whether each check passed, the last 4 digits of the NIN, a one-way code that stops one
          NIN verifying two accounts, and the provider&apos;s reference. We don&apos;t keep your full NIN, your selfie or
          the NIN photo.</li>
        <li><strong>WAEC/NECO result-checker PINs:</strong> stored encrypted and deleted once we&apos;ve reviewed the
          certificate.</li>
        <li><strong>Online lesson recordings:</strong> online lessons are recorded, with the parent&apos;s agreement, and
          may show the child.</li>
        <li><strong>Technical data:</strong> your IP address, used to limit repeated login and sign-up attempts, and the
          login cookie that keeps you signed in. We don&apos;t use advertising or tracking cookies.</li>
      </ul>

      <h2>Why we use it</h2>
      <ul>
        <li>To run the service you signed up for: matching parents and tutors, bookings, lessons, payments, refunds and
          payouts (performing our contract with you).</li>
        <li>To vet tutors before parents see them, which keeps children safe and is why we check NINs, certificates
          and quiz results (our legitimate interest, and your consent when you start the check).</li>
        <li>To record online lessons so problems can be reviewed (the parent&apos;s consent when booking).</li>
        <li>To keep accounts and payments secure, and to keep the financial records the law requires (legal
          obligation and legitimate interest).</li>
        <li>To answer your feedback and questions.</li>
      </ul>

      <h2>Who else handles it</h2>
      <p>We share data only with the services that help us run TutorLink, and only what each one needs:</p>
      <ul>
        <li><strong>Paystack</strong>: your TutorLink account number, deposits, withdrawals and tutor payouts.</li>
        <li><strong>Dojah</strong>: NIN and selfie checks for tutors.</li>
        <li><strong>Google</strong>: signing in with Google, if you choose it.</li>
        <li><strong>Resend</strong>: sending our emails.</li>
        <li><strong>Anthropic (Claude)</strong>: writes quiz questions, and answers questions you type into the help
          chat. The help assistant sees only what you type there, not your account.</li>
        <li><strong>Our file storage provider</strong>: pictures, certificates and lesson recordings, kept private.</li>
      </ul>
      <p>
        Some of these providers process data outside Nigeria. Where they do, we rely on the safeguards the Act allows.
        Within TutorLink, parents and tutors see only what they need: a tutor sees a parent&apos;s first name and
        picture on job posts, and the home address only once an at-home booking is paid. We don&apos;t sell your data.
      </p>

      <h2>How long we keep it</h2>
      <ul>
        <li>Online lesson recordings: deleted 90 days after the lesson, unless a problem reported on that lesson is
          still open.</li>
        <li>Password reset links: work once, for one hour.</li>
        <li>Account, booking and payment records: while your account is open, then for as long as the law requires us
          to keep financial records.</li>
      </ul>

      <h2>Your rights</h2>
      <p>
        You can ask us for a copy of your data, to correct it, to delete it (except records we must keep by law), to
        restrict or object to how we use it, or to withdraw consent you gave. Write to <strong>{detail('email')}</strong>{' '}
        and we&apos;ll reply within 30 days. You can also complain to the Nigeria Data Protection Commission (ndpc.gov.ng).
      </p>

      <h2>Children</h2>
      <p>
        Accounts are for adults: parents, guardians and tutors aged 18 or over. Information about a child is given by
        their parent, who decides what to share.
      </p>

      <h2>Changes</h2>
      <p>If we change this notice, we&apos;ll update the date above and tell you in the app before it takes effect.</p>
    </LegalPage>
  )
}
