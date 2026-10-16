# Spec 12: Admins write the exam questions, and no tutor sees a question twice

Status: **approved** (2026-10-16), requested by the owner.
Changes spec 4 R5.2 (Claude writes the question bank) and R5.3 (unseen questions first): admins now supply the
questions, Claude only tops up, and a tutor never gets a question they've had before. Also moves the help
assistant (spec 6 R3) to the cheaper Claude Haiku model.

## Why

The owner wants control over what tutors are tested on, and to stop depending on Claude for the bank. Retakes
must test the tutor afresh, so a tutor must never meet the same question twice.

## Requirements

### R1. Writing a question
1. At `/admin/exam`, an admin adds a question for **general reasoning**, or for a **subject** (from TutorLink's
   subject list, spec 7) at a **level** (primary, junior secondary, senior secondary, international).
2. A question has its text (10-2,000 characters), exactly **four options** (1-500 characters each, all
   different), the **correct option**, and an optional explanation (up to 2,000 characters) only admins see.
3. The same question text (ignoring capitals and extra spaces) can't be added twice; a duplicate is a 409.

### R2. Uploading a PDF of questions
1. An admin uploads a PDF (up to 10 MB, a text PDF, not a scan or photo) and chooses the subject and level, or
   general reasoning, for all the questions in it.
2. The PDF follows a fixed layout, shown on the page as an example:

   ```
   1. What is 3 x 4?
   A. 7
   B. 12
   C. 34
   D. 1
   Answer: B
   Explanation: 3 groups of 4 make 12.   (optional)
   ```

   Questions are numbered `1.` or `1)`; options are `A.`-`D.` or `A)`-`D)`; the answer line names one letter.
3. TutorLink reads the PDF and shows **every question it found** for the admin to check, fix or remove, and lists
   any part it couldn't read (with the question number and why). Nothing is saved until the admin confirms.
4. Saving adds the checked questions; duplicates (R1.3) are skipped and counted, not an error.
5. A scan, photo or a PDF with no questions in this layout is refused with a message explaining the layout.

### R3. The bank
1. Admin questions and Claude's questions sit in the same bank and are served the same way. Admins see who wrote
   each (an admin's name, or "Claude"), and can retire any question (spec 4 R5.2), which never serves it again.
2. **Claude only tops up**: when a subject and level (or general reasoning) has fewer active questions than its
   target (300 general, 200 per subject and level), and the Claude API key works. If Anthropic rejects the key,
   TutorLink stops asking for an hour instead of failing every pass.
3. Adding questions is recorded in the admin activity log (spec 8), with how many and for which subject.

### R4. No repeats
1. A tutor is **never given a question they've had** in any earlier attempt. Different tutors can share questions.
2. When the bank doesn't hold enough questions the tutor hasn't seen, the attempt isn't started (409, "Your exam
   is being prepared, try again shortly"), Claude is asked to top up if it can, and admins are told in the app which
   subject and level need questions (at most once a day per subject and level).

### R5. The help assistant
1. The help assistant uses **Claude Haiku 5.5** by default (`HELP_MODEL`); it costs a small fraction of Opus.

## Non-goals
- Editing a question after it's saved (retire it and add a corrected one, so past attempts stay as they were).
- Word, Excel or CSV uploads; reading scanned PDFs.
- Images or formulas in questions.

## Acceptance criteria
- [x] R1: an admin adds a general and a subject question; bad input (three options, two the same, an unlisted subject, a level on general) is a 422; a duplicate is a 409; only admins can add.
- [x] R2: a PDF in the layout is read into questions with their answers and explanations, nothing saved; unreadable parts are listed by number; saving adds them and skips duplicates; a PDF without the layout is refused.
- [x] R3: admin questions are served in attempts like Claude's; the list shows who wrote each; adding writes an activity line; a rejected API key stops top-ups for an hour.
- [x] R4: across a tutor's attempts no question repeats; with too few unseen questions the attempt is refused, and admins are told once a day.
- [x] R5: the help assistant calls Claude Haiku 5.5 by default, without the fallback option Haiku doesn't take.
