# Spec 1 of 4: Bookings, prepaid payments, hidden fees and tutor payouts

Status: **approved** (2026-10-07)
Build order: this spec first; specs 2-4 build on it.
Related: [2 Job posts](feature-2-job-posts.md) · [3 Online lessons](feature-3-online-lessons.md) · [4 Tutor onboarding](feature-4-tutor-onboarding.md)

## Why

Today a parent books a tutor and is billed at the end of the month by card, for lessons already given
(`backend/app/domains/billing/`). The business wants:

- Parents pay **before** lessons, by **bank transfer only** (no cards), into an account number unique to them,
  with all money landing in the platform's Paystack balance.
- Tutors get paid **after** lessons, by the admin.
- Two platform fees, each hidden from the other side.
- A way to get money back when a tutor doesn't keep the agreement.

## Current behaviour being replaced

| Today | After this spec |
|---|---|
| A tutor has one `rate_per_session` and a list of subjects | A tutor has **offers**: subjects + weekly availability + one price per lesson (R0) |
| `POST /schedules` books instantly | Parent sends a **booking request**; the tutor accepts or declines |
| Admin generates monthly invoices from confirmed sessions | Parent prepays each billing period before its lessons |
| Card checkout (`POST /invoices/{id}/pay`) | Removed. Bank transfer to the parent's dedicated account number |
| One `COMMISSION_RATE`, taken from the tutor's rate | Parent fee + tutor fee, admin-editable, each hidden from the other side |
| No tutor payouts | Admin payouts page |

## Terms

- **Offer**: something a tutor teaches: one or more subjects at one level, the weekly times they can teach it, and one price per lesson (R0).
- **Agreed price (P)**: price per lesson, whatever the number of subjects in it. For a direct booking it is the price of the tutor's offer; for a job (spec 2) it is the parent's price.
- **Parent fee (S%)** and **Tutor fee (T%)**: platform percentages set by the admin.
- **Parent price per lesson** = P × (1 + S%). **Tutor earning per lesson** = P × (1 − T%).
- **Balance**: a parent's TutorLink balance (wallet). Bank transfers add to it; lesson payments take from it.
- **Billing period**: chosen by the parent per booking. *Daily* = each lesson is paid on its own; *weekly* = lessons Monday-Sunday; *monthly* = lessons in a calendar month.

## Requirements

### R0. Tutor offers and availability
1. When registering, and anytime afterwards, a tutor sets up at least one offer. Each offer has:
   - one or more subjects;
   - one level;
   - one or more weekly availability windows (day, start, end);
   - one price per lesson (> 0).
2. Offers replace today's single `rate_per_session` and `tutor_subjects`. `GET /tutors` filters and sorting work on offers: a tutor matches a subject filter if any offer includes it, and the price shown is their lowest offer price.
3. A tutor can add, edit or remove offers anytime. Changes never affect accepted or active bookings: those keep their subjects, times and price.
4. Removing an offer or window that an active booking uses is allowed. The booking continues unchanged, but new requests can't use it.

### R1. Fees and who sees them
1. Admin can view and change S% and T% (0-50%). Starting values: **S = 10%** (parent fee) and **T = 8%** (tutor fee). Example: P = ₦5,000 → the parent pays ₦5,500, the tutor receives ₦4,600 and TutorLink keeps ₦900. New values apply only to bookings accepted afterwards; an accepted booking keeps the rates it was accepted with (like rule 11 today).
2. Visibility is enforced in API responses, not only in the UI:

| Field | Parent | Tutor | Admin |
|---|---|---|---|
| Agreed price P | yes | yes | yes |
| Parent price per lesson / period total | yes (amount only) | **no** | yes |
| S% | **no** | **no** | yes |
| T% and tutor earning | **no** | yes | yes |
| Platform margin | no | no | yes |

3. Before a parent pays anything, they see the full amount they will pay.
4. The tutor's bank details are returned only to admins. The tutor sees only bank name and the last 4 digits.

### R2. Booking lifecycle
1. A parent requests a booking: tutor, one of the tutor's offers, the subjects from that offer they want (one or more), one or more weekly slots (day, start, end), start date, billing period, lesson mode (`online`/`offline`, see spec 3), and the **child's strengths** and **child's weaknesses** (both required, free text, 10-1,000 characters each). The tutor sees both when deciding whether to accept, and they stay on the booking for the tutor's reference.
2. Each slot must fall inside one of the offer's availability windows, and P is the offer's price at request time. Slots are also clash-checked against the tutor's accepted and active bookings, both on request and on accept (the current rule 3 overlap check, applied to every slot).
3. Statuses: `requested → accepted (awaiting payment) → active → ended`, plus `declined`, `expired`, `released` and `cancelled`.
4. The tutor accepts or declines. A request that isn't answered within **72 hours** expires (confirmed).
5. On accept, the parent is notified ("Your booking has been taken") by email and in the app, with the amount due for the first period and their account number.
6. The first period must be paid **at least 24 hours before its first lesson starts**. If it isn't, the booking is `released` and the tutor's slots become free. A start date must leave time for this: the first lesson must be more than 24 hours after acceptance, otherwise the start moves to the next slot that is.
7. Payment confirms the lessons: as soon as a period is paid, its lessons are confirmed on both timetables, with no further confirmation step. Lessons exist only for paid periods.
8. A parent can cancel an active booking with at least **48 hours' notice** before a paid lesson. Lessons starting 48 or more hours later are refunded (R5.4); lessons sooner than that are not refunded and are taught as normal.
9. Either side can end a booking. An optional end date can be set when booking (spec 2: when posting the job); with none, the booking repeats until ended.

### R3. Paying: dedicated accounts and the balance
1. Each parent gets their own Paystack Dedicated Virtual Account (an account number unique to them) the first time a booking of theirs is accepted. It is shown on their dashboard.
2. A transfer into that account credits the parent's balance once Paystack reports it (`charge.success` webhook). The same rules as today apply: valid signature, processed once, re-verified with Paystack.
3. Any amount can be sent. Whenever the balance covers a period that is due, that period is paid from the balance automatically, oldest due first.
4. Every balance change is a ledger entry (deposit, lesson payment, refund, withdrawal), and the balance always equals the sum of the entries.
5. Next periods: the amount for a booking's next period can be paid as soon as the current period starts. It must be paid **at least 24 hours before the period's first lesson**. The parent is notified when it becomes payable and again 24 hours before the deadline, with the amount and account number. If it isn't paid by the deadline, that period's lessons aren't scheduled and the booking is paused. A booking paused for **7 days** ends.
6. A parent can ask to withdraw their balance to a bank account. Withdrawals go to the admin, like tutor payouts (R6).

### R4. Lessons
1. Paying a period creates its lessons, already confirmed (`confirmed`). Parents no longer confirm lessons after they happen; today's "confirm session" step is removed.
2. The tutor must submit a report (and, for online lessons, the recording: spec 3) within **24 hours** after the lesson ends. A lesson with no report by then is flagged to the admin as a possible absence, and its earning is held until the admin resolves it (as in R5.3).
3. The parent's problem window (R5.1) closes **24 hours** after the report is submitted. If no problem was reported, the tutor earning becomes **payable** then.

### R5. Problems and refunds
1. Until **24 hours** after the tutor submits the lesson report (R4.3), the parent can report a problem: tutor absent, late or left early, agreement broken, or other, with a description. For a lesson with no report, the parent can report until the admin resolves the flag.
2. While a report is open, that lesson's tutor earning is **on hold**.
3. The admin resolves it with one of:
   - **Refund**: the lesson's agreed price P (**excluding** the parent fee) goes back to the parent's balance, and the tutor earns nothing for it.
   - **Reschedule**: a new date and time is set, and the paid lesson moves there.
   - **Reject**: the lesson stands, and the earning becomes payable.
4. Refunds for cancellations (R2.8) go to the admin as a refund request. When the admin approves it, P per refunded lesson (excluding the parent fee) is credited to the parent's balance.
5. Every refund shows on the parent's dashboard as the amount credited to their TutorLink balance. That money can only be used for future lessons or withdrawn (R3.6).
6. The parent and tutor are both notified of the outcome.

### R6. Tutor payouts (admin)
1. A tutor adds payout bank details (bank and account number). The account name is checked with Paystack's account lookup and must match the tutor's name; the admin can override with a note.
2. The admin payouts page lists, per tutor, payable earnings and when the tutor must be paid: **48 hours after the last lesson of the billing period**. For daily billing, that's 48 hours after each lesson. For weekly, 48 hours after the week's last lesson. For monthly, 48 hours after the month's last lesson. Overdue payouts are highlighted.
3. For each tutor, the admin can either **Send via Paystack** (Paystack Transfer to the tutor's bank; the outcome comes from `transfer.success`/`transfer.failed` webhooks) or **Mark as paid** (paid outside the app, with a reference note).
4. Each earning is paid at most once. A failed transfer makes the earning payable again.
5. The tutor sees each earning's status: on hold, payable, paid.

### R7. Notifications (email + in-app list)
Booking requested (tutor) · taken or declined (parent) · payment due with account number (parent) · payment received (parent) · booking released, paused or ended (both) · lesson report submitted (parent) · problem reported and resolved (both) · payout sent (tutor).

## Non-goals
- Card payments of any kind.
- Automatic payouts with no admin action.
- Partial-lesson refunds.
- Moving money between parents.

## Acceptance criteria
- [ ] Parent, tutor and admin responses for the same booking match the R1 visibility table. A test checks that every parent-facing response has no tutor fee or earning fields, and every tutor-facing response has no parent fee or parent total fields.
- [ ] Changing S% or T% doesn't change the amounts of an already-accepted booking.
- [ ] Booking request → accept → transfer webhook → balance credited → first period paid → lessons created. All covered by one test.
- [ ] A tutor can't finish registration without at least one offer. An offer with two subjects has one price.
- [ ] A booking slot outside the offer's availability windows is a 422.
- [ ] Editing an offer's price or times after a booking is accepted doesn't change that booking.
- [ ] With S = 10% and T = 8%, a ₦5,000 lesson shows ₦5,500 to the parent and ₦4,600 to the tutor.
- [ ] A booking request without the child's strengths or weaknesses is a 422. The tutor sees both on the request.
- [ ] An accepted booking not paid 24 hours before its first lesson is released, and its slots can be booked again.
- [ ] Paying a period creates its lessons already confirmed. There is no parent confirm endpoint.
- [ ] A lesson's earning becomes payable 24 hours after its report if no problem is reported. A lesson with no report 24 hours after it ends is flagged and its earning held.
- [ ] Cancelling with 48 or more hours' notice creates a refund request for those lessons. Cancelling with less refunds nothing.
- [ ] A weekly booking's earnings are due for payout 48 hours after the week's last lesson.
- [ ] An unanswered request expires after 72 hours.
- [ ] A duplicate or forged deposit webhook doesn't credit the balance twice or at all.
- [ ] The balance equals the sum of ledger entries after every operation tested.
- [ ] An approved refund credits P per lesson (not P × (1 + S%)) to the balance, and the tutor earning becomes void.
- [ ] Earnings under an open problem report never appear as payable.
- [ ] An earning can't be paid twice, and a failed transfer makes it payable again.
- [ ] Tutor bank account number is absent from every non-admin response except the tutor's own last 4 digits.
- [ ] `POST /invoices/{id}/pay` and card checkout are gone from the backend and frontend.

## Assumptions
- There is no production data. Existing schedules, sessions and invoices are dev or test data, so the old monthly invoice tables can be replaced instead of migrated.
- Paystack enables Dedicated Virtual Accounts and Transfers on the platform account. Until then, everything is built and tested against fakes and Paystack test mode.
- Background jobs (expiry, release, flags, payable earnings, due periods) run on a schedule inside the app at least every 15 minutes.
