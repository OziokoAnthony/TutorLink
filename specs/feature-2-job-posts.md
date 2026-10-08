# Spec 2 of 4: Job posts

Status: **approved** (2026-10-07)
Depends on: [1 Bookings and payments](feature-1-bookings-and-payments.md) (terms P, S%, T%, booking lifecycle)

## Why

Today a parent can only pick a tutor from `/tutors`. Parents also want to describe what they need, with the
qualifications they want and the price they will pay, and let tutors come to them.

## Requirements

### R1. Posting a job (parent)
1. A parent creates a job with these fields:
   - one or more subjects, one level, lesson mode (`online`/`offline`)
   - area (required for offline)
   - the weekly times they want (one or more slots), start date, optional end date, billing period
   - qualifications wanted (free text, plus optional minimum certificate type from spec 4)
   - other requirements (free text)
   - one price per lesson (P, > 0), whatever the number of subjects
   - **child's strengths** and **child's weaknesses** (both required, free text, 10-1,000 characters each)
2. Job statuses: `open → ongoing → completed`, or `closed` (by the parent, only while open).
   - **open**: has no limit; it stays up until the parent picks a tutor or closes it.
   - **ongoing**: from the moment the parent picks a tutor, for as long as the resulting booking is awaiting payment or active.
   - **completed**: set automatically when that booking ends (spec 1 R2.3). A completed job is no longer shown to tutors.
3. A parent can edit an open job anytime, including subjects, times and price. Existing applicants are notified of the change and their applications stay; any applicant whose bookings now clash with the new times is withdrawn automatically and told why. An ongoing or completed job can't be edited.

### R2. Browsing and applying (tutor)
1. Only **approved** tutors can browse and apply.
2. The tutor job list shows open jobs only. It can be filtered by subject (a job matches if it includes that subject), level, mode and area. Which countries' jobs a tutor sees: spec 5 R4.
3. Each job shows P, and **to the tutor only**, T% and their earning per lesson P × (1 − T%).
4. Tutors never see the parent fee, the parent's total, or the parent's surname, address, phone or email. They see the parent's first name and profile picture, the area, and the child's strengths and weaknesses.
5. When the tutor is chosen, the booking carries the job's strengths and weaknesses (spec 1 R2.1).
6. A tutor applies at most once per job, with an optional note of up to 1,000 characters. They can withdraw while the job is open.
7. A tutor can't apply if any job slot clashes with their accepted or active bookings.

### R3. Choosing a tutor (parent)
1. On their job, the parent sees the list of tutors who applied. They can open each applicant's full public profile (as `GET /tutors/{id}` today: photo, rating, reviews, offers, verification badges from spec 4) and read their note, then select the one they're interested in.
2. Accepting an applicant creates a booking from the job: same subjects, slots, P, mode and billing period. The booking goes straight to **accepted (awaiting payment)**, and the rest follows spec 1 R2.5 onward.
3. The job becomes `ongoing`. Other applicants are notified that the job was taken.
4. If the booking is released (unpaid) or declined, the job goes back to `open` and its other applications stay active.
5. When the booking ends, the job becomes `completed` automatically.

### R4. Notifications
New applicant (parent) · chosen (tutor) · job taken (other applicants) · job completed (parent).

## Non-goals
- Tutors counter-offering a different price.
- Messaging between parent and tutor before acceptance.
- Showing jobs to the public or to parents other than the owner.

## Acceptance criteria
- [x] An unapproved or pending tutor gets 403 on job browse and apply.
- [x] A job seen by a tutor has no parent fee, parent total, surname or contact fields. A job seen by its parent has no T% or tutor earning fields.
- [x] A job without the child's strengths or weaknesses is a 422. Tutors browsing see both, and the parent's first name and picture.
- [x] A job with three subjects has one price, and appears in a tutor search for any of the three.
- [x] Editing an open job notifies its applicants. Editing an ongoing or completed job is a 409.
- [x] Applying twice to the same job is a 409. Applying with a clashing slot is a 409.
- [x] Selecting an applicant creates a booking in "awaiting payment" with the job's P and slots, sets the job to `ongoing`, removes it from tutor browse, and notifies the other applicants.
- [x] An open job with no applicants is still open after any amount of time.
- [x] When the booking is released, the job is `open` again. When the booking ends, the job is `completed`.
- [x] The parent can list applicants on their own job and open each applicant's profile.
- [x] Only the owning parent can view applicants, edit, close or accept.
