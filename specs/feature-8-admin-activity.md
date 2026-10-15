# Spec 8: Admin names, welcome and activity log

Status: **approved** (2026-10-15), requested by the owner.
Builds on the Admins page (super admin, PR #10).

## Why

Admins have only an email, and nothing records what they do. The owner (the super admin) wants to be greeted by
name, be reminded what they did last time, and see what every other admin did. Every other admin should get the
same welcome and reminder for themselves, but never see the super admin's activity.

## Requirements

### R1. Admin names
1. Every admin has a name (2-80 characters). The super admin types it when adding an admin (spec: Admins page).
2. Every admin can change their own name at `/admin/admins`.
3. An admin with no name yet (the super admin, made before this spec) is asked for it on their dashboard and
   greeted by email until then.

### R2. Activity log
1. TutorLink records, for each admin: logging in, changing their password, and every admin action that succeeds:
   vetting a tutor, correcting a tutor's name, removing a profile picture, reviewing a certificate, retiring an
   exam question, approving or rejecting a job post, approving or rejecting a refund, resolving a lesson problem,
   paying a tutor, overriding a tutor's bank account, sending / marking paid / rejecting a withdrawal, changing the
   fees, replying to feedback, adding / removing / restoring a subject, publishing a legal page, adding or removing
   an admin, and changing their name.
2. Each entry is one plain-English line naming the item, e.g. "Approved tutor Ada Obi", "Approved a ₦5,000.00
   refund for Chika Eze", "Added subject Data Science", written when it happens (it doesn't change if a name
   changes later), with the time.
3. A failed or refused action is not recorded. Entries can't be edited or deleted through the app.
4. Recording starts when this spec goes live; earlier actions aren't in the log.

### R3. Sessions
1. A session starts when an admin logs in and lasts until their next login.
2. "Last session" is the session before the current one: when it started and what the admin did in it. On an
   admin's first login there is no last session.

### R4. The admin dashboard (`/admin`)
1. Admins land on `/admin` after logging in. It says "Welcome, <name>".
2. It shows the admin's last session (start time and actions, newest first, or "Nothing changed" if none) and
   their most recent 50 actions.
3. The super admin also sees **Team activity**: the latest 100 actions of the other admins, each with the admin's
   name, and can filter it to one admin.
4. An ordinary admin sees only their own sessions and actions. Asking the API for anyone else's, including the
   super admin's, is a 403; no response to an ordinary admin ever contains another admin's activity.

## Non-goals
- Recording what admins only looked at (reads), or the IP address and device of a session.
- Exporting or searching the log; deleting old entries.
- Activity logs for parents and tutors.

## Acceptance criteria
- [x] R1: the super admin adds an admin with a name; that admin changes it; the dashboard greets each by name, and an admin with no name by email.
- [x] R2: each listed admin action writes one line naming the item, and a refused action (403/404/409/422) writes nothing.
- [x] R3: after a second login, "last session" is the first login's session with the actions done in it.
- [x] R4.3: the super admin sees the other admins' actions with their names and can filter by admin.
- [x] R4.4: an ordinary admin gets only their own activity; asking for team activity or another admin's is a 403, and the super admin's actions never appear.
