# Spec 9: Parents and tutors agree to their own legal documents

Status: **approved** (2026-10-15), requested by the owner.
Changes spec 7 R2 (one shared set of documents, which nobody accepts): parents and tutors now have their own
documents, and must agree to the latest version of each.

## Why

TutorLink needs proof that every parent and tutor read and agreed to the privacy notice, terms of service and
disclaimer that apply to them. Parents and tutors have different relationships with TutorLink (parents pay, tutors
are paid and come into homes), so each gets its own documents.

## Requirements

### R1. Documents per role
1. There are six documents: a **privacy notice**, **terms of service** and **disclaimer** for **parents**, and the
   same three for **tutors**. They start as copies of today's three documents.
2. `/admin/legal` edits each of the six as today (plain text, versions kept, optional in-app notice; spec 7 R2).
3. The public pages `/privacy`, `/terms` and `/disclaimer` show the parents' version by default, with a switch to
   the tutors' version. A logged-in parent or tutor sees their own.

### R2. Agreeing
1. A parent or tutor agrees to all three of their documents at once: they see the three latest versions, tick
   "I have read and agree to the Terms of Service, Privacy Notice and Disclaimer", and press **I agree**.
2. TutorLink stores each agreement as proof: who, which version of which document, when, and from which IP
   address. Agreements are never edited or deleted.
3. Agreeing is only accepted for the latest versions; an older version is a 409 (someone published meanwhile).
4. A parent or tutor can always read their documents and see when they agreed, from their dashboard.

### R3. Parents
1. Right after signing up (with email or Google), a parent must agree before using TutorLink.
2. Until they agree, every parent action is refused (403, "Please read and agree to TutorLink's terms to
   continue."), except reading their account and notifications, reading the documents, agreeing, and logging out.

### R4. Tutors
1. Agreeing is the **last step of the onboarding checklist** (spec 4 R2): it can be done once the picture, NIN,
   certificate and exam steps are done.
2. An admin can't approve a tutor who hasn't agreed ("terms not agreed" in what's missing for approval).
3. Before that, a tutor uses onboarding as today; they don't have to agree to start the checklist.

### R5. New versions
1. When an admin publishes a new version of a document, everyone in that document's audience must agree again.
2. A parent, or a tutor who has agreed before, can't continue until they agree to the new version (as R3.2).
   A tutor who has never agreed is still only held back from approval (R4).
3. At the moment this spec goes live, every existing parent and every approved tutor must agree on their next
   visit; tutors still onboarding get the new checklist step.

### R6. Admins
1. Admins don't agree to anything; R3 and R5 don't apply to them.
2. Publishing a document is still recorded in the admin activity log (spec 8), naming the audience.

## Non-goals
- Agreeing to one document but not the others.
- Showing admins a list of who has agreed (the proof is stored; a report can come later).
- Emails asking people to agree (the in-app notice from spec 7 R2.4 still exists).

## Acceptance criteria
- [x] R1: the six documents exist, each with its own versions; the public pages give the parents' version by default and the tutors' on request.
- [x] R2: agreeing records one row per document with the version and IP; agreeing to an old version is a 409.
- [x] R3: a new parent (email or Google) is refused every parent action until they agree, but can read their account and the documents, agree and log out.
- [x] R4: the agreement step unlocks after the other steps; a tutor who hasn't agreed can't be approved, and can still do their onboarding.
- [x] R5: after a new parent terms version, an agreed parent is refused until they agree again; tutors are unaffected by a parent document, and vice versa.
- [x] R6: admins are never asked to agree.
