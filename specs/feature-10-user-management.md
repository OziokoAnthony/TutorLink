# Spec 10: Parents and tutors at a glance, and removing accounts with notice

Status: **approved** (2026-10-16), requested by the owner.

## Why

Admins can't see how many parents and tutors have signed up, how far tutors are through onboarding, or who still
uses TutorLink. They also need a fair way to close accounts that are no longer used: with a notice first, and
never while money or lessons are outstanding.

## Requirements

### R1. Last seen
1. TutorLink records when each parent and tutor last used it: on login, and on any request while logged in (at
   most once an hour, to keep writes low).
2. Recording starts when this spec goes live. Until someone is seen, their sign-up time counts as last seen.

### R2. Activity bands
1. **Active**: last seen within 90 days. **Inactive**: 90-180 days ago. **Inactive for a while**: over 180 days.
2. An account under a removal notice is **notice sent**; a removed account is **removed**. These replace the band.

### R3. The overview (`/admin/users`)
1. For parents and for tutors: how many have registered, and how many are active, inactive, inactive for a while,
   under notice, and removed.
2. For tutors also: how many are onboarding (not approved yet), approved, and rejected.
3. A list below, filterable by role, band, and (for tutors) onboarding status, and searchable by name or email.
   Each row: name, email, role, joined, last seen, band, onboarding status (tutors), and anything outstanding.

### R4. Outstanding money and lessons
1. A **parent** has something outstanding when their TutorLink balance isn't ₦0, or a booking is requested,
   accepted, active or paused.
2. A **tutor** has something outstanding when they have earnings not yet paid (pending, on hold or payable), or a
   lesson that is confirmed, reported, disputed or flagged.
3. The list shows what's outstanding in words, e.g. "₦20,000.00 balance", "2 upcoming lessons",
   "₦15,000.00 not paid yet".

### R5. Removal notice
1. An admin can send a removal notice to a parent or tutor with nothing outstanding, with a reason (10-1,000
   characters) the person sees. With something outstanding it's refused (409, naming what's outstanding).
2. The person is told in the app and by email: their account will be closed on a date 14 days later, why, and that
   they can reply through Help & feedback to keep it. While the notice runs, their dashboard shows the same message
   as a banner. They can still use TutorLink normally.
3. An admin can cancel a notice at any time; the person is told in the app that their account will stay open.

### R6. Removing
1. Once the 14 days have passed, the account shows as **ready to remove**, and an admin can remove it. Before
   then, removing is refused (409).
2. Removing checks R4 again: if something became outstanding during the notice, it's refused (409).
3. A removed account can't log in (email or Google), all its sessions end, a tutor disappears from search and
   their profile, and a parent's open or pending job posts are closed. Bookings, payments, lessons and receipts
   are kept. The person is emailed that their account was closed.
4. An admin can restore a removed account: it can log in again with the same password, and is told by email.
5. Admin accounts are never listed, noticed or removed here (spec 8's Admins page handles them).

### R7. Activity log
1. Sending and cancelling a notice, removing and restoring are recorded in the admin activity log (spec 8),
   naming the person.

## Non-goals
- Removing accounts automatically, or reminders during the notice.
- Erasing personal data (records are kept; erasure can be a later spec).
- A way for the person to cancel the notice themselves (they reply through Help & feedback).

## Acceptance criteria
- [x] R1: logging in and using the API sets last seen, at most once an hour; someone never seen counts from sign-up.
- [x] R2, R3: the counts by role and band (and tutors' onboarding status) match the accounts; the list filters by role, band, onboarding status and search, and shows last seen and what's outstanding.
- [x] R4, R5.1: a notice to a parent with a balance or an unfinished booking, or a tutor with unpaid earnings or a coming lesson, is a 409 naming it; without, it's sent with the reason and a closing date 14 days later.
- [x] R5.2, R5.3: the person gets the notice in the app and by email and sees it on their dashboard; cancelling tells them and removes it.
- [x] R6: removing before 14 days, or with something outstanding, is a 409; after, the person can't log in, is hidden from search, their open jobs close, and they're emailed; restoring lets them log in again.
- [x] R6.5: admins aren't listed and can't be noticed or removed here.
- [x] R7: notice, cancel, remove and restore each write an activity line naming the person.
