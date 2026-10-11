# Spec 6: Feedback and the help assistant

Status: **approved** (2026-10-09)
Independent of specs 1-5.

## Why

Parents and tutors have no way to tell TutorLink what's wrong, what they'd like, or to ask how something
works. The business wants their feedback in one place where an admin can read it and answer, and a help
assistant that answers everyday questions at once.

## Requirements

### R1. Sending feedback (parents and tutors)
1. A logged-in parent or tutor sends feedback from their dashboard ("Help & feedback"): a type (problem,
   suggestion, praise or question) and a message of 10-2,000 characters.
2. They see everything they've sent, newest first, with TutorLink's reply under each.
3. At most **10 messages per hour** per user.
4. Admins can't send feedback, and visitors without an account can't either.

### R2. Answering feedback (admin)
1. `/admin/feedback` lists feedback in two tabs: **Waiting** (no reply yet, oldest first) and **Answered**
   (newest first). Each shows the sender's name, email and role, the type, the message, and the help chat
   conversation when there is one (R3.4).
2. Each new message notifies admins in the app (no email).
3. An admin replies once, 3-2,000 characters. The sender is notified in the app and by email, with the reply.
   Replying to answered feedback is a 409.

### R3. Help assistant
1. Parents and tutors can open a help chat on any dashboard page. Claude answers questions about how
   TutorLink works, for the reader's role, from a fixed description of the product in the prompt.
2. The assistant can't see the user's account, bookings, lessons or money, and says so. It never states
   fee percentages or another side's amounts; it points to the user's own dashboard for figures.
3. When it can't help, or the user asks for a person, it says to send the conversation to the TutorLink team.
4. "Send to the TutorLink team" turns the conversation into feedback (type question) with the
   conversation attached, which reaches admins as in R2.
5. The conversation lives in the browser only; nothing is stored until it is sent to the team. At most
   **30 questions per hour** per user, 40 messages per conversation, 4,000 characters per message.
6. Without a Claude API key, or when Claude fails or declines, the chat says it isn't available and offers
   the feedback form instead (503).

## Non-goals
- Feedback from visitors without an account.
- Live chat with a person; replies are asynchronous.
- The assistant reading or changing account data.
- Threads with more than one reply.

## Acceptance criteria
- [x] R1: a parent and a tutor each send feedback and see it, with the reply once there is one; an admin gets 403.
- [x] R1.1: a message under 10 or over 2,000 characters is a 422.
- [x] R2: admins list waiting and answered feedback; a reply notifies and emails the sender; a second reply is a 409.
- [x] R3: the help chat returns Claude's answer for the reader's role; with no key it's a 503.
- [x] R3.4: a conversation sent to the team arrives as a question with the conversation attached.
