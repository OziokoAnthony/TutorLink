# Spec 15: Nursery and exam-prep levels, a guardian rule for young children, and "How did you hear about us?"

Status: **approved** (2026-10-16), requested by the owner, after comparing with educere.com.ng.

## Why

Parents look for help before primary school and for exam preparation and adult learning, which TutorLink's levels
don't cover. Young children shouldn't be alone with a tutor. And the owner wants to know which marketing works.

## Requirements

### R1. Two new levels
1. Besides primary, junior secondary, senior secondary and international, there are **Nursery & pre-primary** and
   **Exam prep & adult learning**. Tutors offer them, parents book and post jobs at them, search and the public pages
   (spec 14) show them, and exam questions can be written for them (spec 12).
2. Exam-prep and language subjects (e.g. JAMB, IELTS, SAT, French) are added by admins at `/admin/subjects`
   (spec 7); nothing is added automatically.

### R2. A parent or guardian present for young children
1. A booking or job post at **Nursery & pre-primary** or **Primary** needs the parent to confirm: "If my child is
   under 8, a parent or guardian will be present during every lesson." Without it, it's refused (422).
2. TutorLink stores when they confirmed, and the tutor sees it on the booking and the job.
3. Admins should add the same rule to the parents' terms (`/admin/legal`, spec 9); the code doesn't edit legal text.

### R3. How did you hear about TutorLink?
1. Sign-up (email or Google, parents and tutors) asks, optionally: Google search, Instagram, Facebook, TikTok,
   WhatsApp, a friend or family member, a school or school event, a tutor, or something else.
2. The Parents & tutors page (spec 10) shows how many parents and tutors chose each answer, and "Not answered".

## Non-goals
- Asking the child's age or date of birth.
- Changing the answer after sign-up; tracking ad campaigns.

## Acceptance criteria
- [x] R1: a tutor offers each new level, a parent books it and posts a job at it, and the public level pages exist for both.
- [x] R2: a booking or job at nursery or primary without the confirmation is a 422, with it is stored and shown to the tutor; other levels don't ask.
- [x] R3: sign-up stores the answer (or none), an invalid answer is a 422, and the overview counts by answer.
