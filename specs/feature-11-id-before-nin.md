# Spec 11: Tutors can start with an ID document and verify their NIN within 90 days

Status: **approved** (2026-10-16), requested by the owner.
Changes spec 4 R2.3 and R3 (NIN verification before approval) and R4 (certificates only after the NIN).

## Why

NIN verification can be slow or fail for reasons outside a tutor's control. Tutors should be able to start with
a valid ID document an admin checks, and still verify their NIN, which is the stronger check, within 90 days.

## Requirements

### R1. ID documents
1. A tutor can upload a picture or scan of one valid ID: **NIN slip or card**, **voter's card**, **driver's
   licence**, or **international passport** (PDF, JPG or PNG, up to 10 MB, recognised by content as certificates
   are). It's private: only the tutor and admins can open it, through short-lived links.
2. An admin reviews it like a certificate: checks the name matches the tutor and the document looks genuine, then
   verifies it or rejects it with a note the tutor sees. The tutor is told in the app and by email.
3. A rejected ID can be replaced. A tutor has at most one ID waiting for review at a time.
4. ID documents are kept after the NIN is verified.

### R2. Identity in onboarding
1. The checklist's identity step is done when the tutor's **NIN is verified** or an **ID document is verified**.
   It offers both: verify the NIN now, or upload an ID and verify the NIN later.
2. Certificates can be uploaded, and the qualifying exam taken, once the NIN is verified or an ID document has been
   uploaded (spec 4 R4 and R5 used to need the NIN first).
3. An admin can approve a tutor whose identity is confirmed either way, with every other step done (spec 4 R2.3,
   spec 9 R4). Only a verified NIN locks the tutor's name (spec 4 R3.5).

### R3. The 90-day NIN deadline
1. A tutor must verify their NIN within **90 days of registering**. Their checklist and dashboard show the date.
2. A tutor whose NIN isn't verified by then is **not visible to parents**: they don't appear in search, their
   profile and availability can't be opened, they can't be booked, can't browse or apply for jobs, and a parent
   can't choose them from a job's applicants. They can't be approved either.
3. Work that started before then **carries on until it ends**: bookings already requested or running (including
   their later paid periods), their lessons, reports and payouts.
4. Verifying the NIN at any time makes them visible again at once (if approved).
5. Reminders in the app and by email **30, 7 and 1 days** before the deadline, and once when it passes, each
   with the date and a link to verify. Each is sent once.

### R4. Admins
1. Admins see the ID documents waiting for review, with the tutor's name, and verify or reject them.
2. Reviewing an ID is recorded in the admin activity log (spec 8).
3. On the Parents & tutors page (spec 10) a tutor past the deadline without a NIN shows "NIN overdue".

## Non-goals
- Checking ID documents automatically with an outside service.
- A deadline other than 90 days, or extending one tutor's deadline.

## Acceptance criteria
- [x] R1: a tutor uploads an ID of each type (not other files); only they and admins can open it; an admin verifies or rejects it with a note and the tutor is told; a rejected one can be replaced; only one waits at a time.
- [x] R2: with a verified ID and no NIN, the identity step is done, certificates can be uploaded, and the tutor can be approved; with only a pending ID they can upload certificates but not be approved.
- [x] R3.2, R3.4: an approved tutor without a NIN is in search and bookable until day 90; after it they're hidden, can't be booked or apply, and can't be approved; verifying the NIN brings them back.
- [x] R3.3: a booking requested before day 90 can still be accepted and paid after it, and its lessons are created.
- [x] R3.5: reminders go out at 30, 7 and 1 days before and when it passes, each once; none for a tutor with a NIN.
- [x] R4: reviewing an ID writes an activity line; the Parents & tutors list shows "NIN overdue".
