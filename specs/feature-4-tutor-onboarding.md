# Spec 4 of 4: Google sign-in, profile pictures and tutor onboarding (NIN, certificates, quiz)

Status: **approved** (2026-10-07)
Independent of specs 1-3, except that approved status gates job applications (spec 2).

## Why

Today a tutor registers with email and password, and the admin approves them by reading their profile
(`PATCH /tutors/{id}/vet`). The business wants faster sign-up with Google, and stronger vetting:
identity checked against the national NIN database, certificates authenticated, and a subject quiz.

## Requirements

### R1. Google sign-in (parents and tutors)
1. Register and login pages have **Continue with Google**.
2. The backend accepts a Google ID token, verifies its signature, audience (our Client ID) and expiry, and requires `email_verified`.
3. If an account exists for that email, the user is logged in. If not, the user picks Parent or Tutor and completes the same profile fields as email sign-up, then gets an account with no password.
4. Accounts made with Google log in with Google only; adding a password to them is out of scope.
5. Admin accounts can't sign in with Google. They keep using password only.

### R1b. Profile pictures (parents and tutors)
*Built together with spec 1, since booking requests require a parent picture.*

1. Parents and tutors each have one profile picture: JPG, PNG or WebP, at most 5 MB, resized to 512×512 and stored in R2.
2. It is **required**:
   - a parent must have one before requesting a booking or posting a job;
   - a tutor must have one before taking the NIN step (it is part of the "Profile" step).
3. When signing up with Google, the Google account photo is offered as the starting picture, and the user can replace it.
4. Who sees it:
   - **Tutor photo**: everyone, on `/tutors`, tutor profiles, booking requests and job applications.
   - **Parent photo**: the parent, admins, and tutors: on the parent's job posts (spec 2 R2.4), booking requests to that tutor, and bookings.
5. Users can change their picture anytime. Admins can remove an inappropriate picture, and the user is then asked to upload a new one.
6. The admin vetting page shows the tutor's profile picture next to the NIN-verified name.

### R2. Onboarding checklist (tutor)
1. A new tutor sees a checklist: Profile (profile picture, and at least one offer with subjects, available times and price per lesson, spec 1 R0) → NIN → Certificates → Quiz → Waiting for admin review.
2. A tutor stays `pending` and hidden from `/tutors` until approved (existing rule 2).
3. The admin can approve only when NIN is verified, at least one certificate is verified, and the quiz is passed. Rejecting is always allowed.
4. Approval makes the tutor a **Verified tutor**: listed on `/tutors` with a "Verified tutor" badge, able to receive booking requests and apply for jobs. **Passing the quiz is mandatory**: no tutor is approved without a passed attempt.

### R3. NIN verification (Dojah)
1. Tutors register with their name **exactly as it appears on their NIN record**, in separate fields: first name, middle name (if the NIN record has one) and surname. The registration form says so.
2. The tutor enters their 11-digit NIN and takes a selfie in the browser.
3. The backend calls Dojah's NIN lookup with selfie verification and records whether:
   - the NIN exists;
   - the name matches **exactly**: first name, middle name and surname each equal the NIN record's, ignoring only capital letters and extra spaces. A missing, extra, reordered or differently spelt name is a mismatch;
   - the selfie matches the NIN photo, above Dojah's confidence threshold.
4. Verified only when all three pass. **There is no override**: on any failure the tutor can't proceed to certificates or the exam. The tutor sees which check failed. On a name mismatch, the message is "Your name doesn't match your NIN record". The NIN record's name itself is not shown, so a stranger's NIN can't be used to learn their name.
5. A tutor with a name mismatch can correct their name and try again. Once verified, the tutor's name is **locked**: it can't be changed by the tutor, only by an admin.
6. Each NIN can verify only one TutorLink account. A NIN already verified on another account is rejected.
7. Stored: verified yes/no, last 4 NIN digits, a one-way hash of the NIN (to enforce point 6), Dojah reference, time. **The full NIN, NIN photo and selfie are not stored.**
8. At most **3 attempts per 24 hours** per tutor, because each lookup costs money.
9. The admin vetting page shows the verified name and the result of each check.

### R4. Certificates (upload + admin review)
1. The tutor uploads one or more certificates:
   - files: PDF, JPG or PNG, at most 10 MB, stored privately in R2
   - type: WAEC, NECO, NABTEB, NCE, Degree, PGDE, TRCN, Other
   - institution and year
2. For **WAEC/NECO**, the tutor also gives the exam number, exam year and a result-checker PIN, so the admin can confirm the result on the exam body's official site. The PIN is stored encrypted and deleted once the certificate is reviewed.
3. The admin views each certificate next to the NIN-verified name. They mark it **verified** or **rejected**, with a note. The tutor sees the result and can upload a replacement for a rejected one.
4. Approved tutors' public profiles show badges: "NIN verified" and certificate types verified. No files or numbers are shown.

### R5. Qualifying exam (quiz)
1. The quiz is TutorLink's **qualifying exam**. A tutor takes it from their dashboard after logging in, and passing it is the step that completes their registration (R2). No tutor becomes a Verified tutor without passing.
2. **Questions are generated automatically** with the Claude API (Anthropic) into a question bank. They aim at complex, multi-step critical-thinking and problem-solving questions, not recall.
   - Each question is multiple choice with 4 options and one correct answer, a short explanation, and a tag: either **general reasoning** or a **subject + level**.
   - Every generated question is checked by a second, independent Claude call that answers it without seeing the key. If its answer differs from the key, the question is discarded.
   - The bank is topped up in the background, so there are always at least **200 questions per subject and level** in use by tutors' offers, and **300 general reasoning** questions.
   - The admin can browse the bank and retire any question. Retired questions are never served again.
3. Each attempt has **20 questions**: 10 general reasoning and 10 from the subjects and levels in the tutor's offers, spread across their subjects. A question the tutor has already seen isn't repeated while unseen ones remain.
4. Time limit **30 minutes**, measured on the server. Answers after the deadline aren't counted.
5. Correct answers and explanations are never sent to the browser before the attempt is submitted. After submitting, the tutor sees only their score and pass/fail, not the answers, so the bank stays useful.
6. Pass mark **70%** (14 of 20).
7. **Attempts:** a tutor can retake until they pass, **up to 6 attempts**. After the 6th failed attempt, the quiz is locked for **24 hours** from that attempt. Then the count resets and they get 6 more.
8. If the bank can't fill an attempt yet (e.g. a newly added subject), the tutor sees "Your exam is being prepared, try again shortly", and generation for that subject is started immediately.
9. The admin sees every attempt's score, date and time taken.

## Non-goals
- Automatic certificate verification with exam bodies or universities.
- Other social logins (Apple, Facebook).
- Google sign-in for admins.

## Acceptance criteria
- [ ] A forged, expired, wrong-audience or unverified-email Google token gets 401.
- [ ] A Google login for an existing email signs into that account. For a new email it requires a role and profile.
- [ ] A parent without a profile picture gets 409 on booking request and job post. A tutor without one can't start the NIN step.
- [ ] A picture over 5 MB or not JPG/PNG/WebP is rejected.
- [ ] A parent's picture is shown to tutors on that parent's job posts, booking requests and bookings, and isn't returned to unauthenticated users.
- [ ] Approving a tutor without verified NIN, a verified certificate and a passed quiz is a 409, naming what's missing.
- [ ] No API response or database column contains a full NIN, selfie or NIN photo.
- [ ] NIN verification fails when any name part differs from the NIN record (spelling, missing middle name, swapped order), passes when only capital letters or spacing differ, and the tutor can't start certificates or the exam until it passes.
- [ ] A name-mismatch response doesn't include the NIN record's name.
- [ ] A verified tutor can't change their name. A NIN already verified on another account is rejected.
- [ ] A 4th NIN attempt within 24 hours is a 429. Dojah is faked in tests.
- [ ] Quiz questions sent to the browser contain no correct-answer field. An answer submitted after 30 minutes isn't scored.
- [ ] A tutor can take attempts 1-6. A 7th attempt within 24 hours of the 6th is a 429. After 24 hours, 6 more are allowed.
- [ ] 14/20 passes and 13/20 fails.
- [ ] A generated question whose independent check gives a different answer is not added to the bank. Claude is faked in tests.
- [ ] The submit response contains the score and pass/fail but no correct answers.
- [ ] A WAEC/NECO checker PIN is unreadable in the database and gone after review.
- [ ] Certificate files are only reachable by the tutor who uploaded them and by admins.

## Assumptions
- An Anthropic API key (for exam generation), a Google OAuth Client ID, a Dojah account (app ID + secret key, sandbox first) and the R2 bucket from spec 3 are provided.
- Existing approved tutors are dev or test data and needn't redo onboarding.
