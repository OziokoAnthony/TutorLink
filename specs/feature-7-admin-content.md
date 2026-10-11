# Spec 7: Subjects and legal pages, managed by admins

Status: **approved** (2026-10-11), requested by the owner.
Changes spec 4 R5.2 (subjects come from a fixed list): the list now lives in the database and admins keep it.

## Why

Adding or removing a subject, or changing a word of the privacy notice or terms, needs a developer today. The
business wants admins to do both, and a disclaimer page alongside the privacy notice and terms.

## Requirements

### R1. Subjects
1. The subjects tutors can offer and parents can post jobs for are kept in the database, each in a group:
   **Nigerian curriculum** or **International**. They start as today's list.
2. `/admin/subjects` lists every subject with its group, whether it's offered, and how many active tutor offers
   use it. An admin adds a subject (name and group) or removes one.
3. A name is 2-60 characters of letters, digits, spaces and `& ( ) - ' . , /`, and is unique ignoring capitals
   and extra spaces. A duplicate is a 409.
4. Removing a subject hides it from new offers, job posts and the search filters. Existing offers, jobs and
   bookings keep it, and the qualifying exam still covers it for tutors who already teach it. A removed subject
   can be restored.
5. Offers and jobs accept only offered subjects, matched ignoring capitals and extra spaces (as spec 4). Anything
   else is a 422. Subject names still reach Claude's exam prompt only from this list, fenced as data.
6. Anyone can read the offered subjects (sign-up needs them before login).

### R2. Legal pages
1. There are three documents: the **privacy notice**, the **terms of service** and the **disclaimer**, at
   `/privacy`, `/terms` and `/disclaimer`, linked from the footer.
2. `/admin/legal` edits each one in plain text: a blank line starts a new paragraph, a line starting `## ` is a
   heading, a line starting `- ` is a bullet, and `**text**` is bold. Nothing else is interpreted, so no HTML or
   script can be added. The page shows a preview.
3. Saving publishes a new version at once. Earlier versions are kept, and the admin sees who published each and
   when. The public page shows the latest version and its date.
4. When publishing, the admin can choose to tell every parent and tutor in the app that the document changed
   (no email).
5. Each document is 100-50,000 characters.
6. The starting versions are the current drafts. A page whose text still contains `[` … `to be filled in]` shows a
   "draft" banner.

### R3. Disclaimer
1. The disclaimer says that TutorLink connects parents with independent tutors and doesn't guarantee results, that
   the help assistant's answers come from AI and may be wrong, that third-party services (video calls, banks) are
   outside TutorLink's control, and points to the terms for liability.
2. The help chat links to it.

## Non-goals
- Renaming a subject (remove it and add the new name; existing offers keep the old one).
- Subjects per level.
- Users accepting each new version of the terms.

## Acceptance criteria
- [x] R1: an admin adds a subject, a tutor can then offer it and a parent post a job with it; after it's removed both are a 422, an existing offer keeps it, and it can be restored.
- [x] R1.3: a duplicate name (any capitals) is a 409; a name with other characters is a 422.
- [x] R1: only admins can add, remove or list all subjects; anyone can read the offered ones.
- [x] R2: an admin publishes a new version of each document; the public page returns the latest; earlier versions are kept; only admins can publish.
- [x] R2.4: publishing with notify tells every parent and tutor in the app, and without it tells nobody.
- [x] R2.2: the text is shown as text: `<script>` in a document appears literally.
