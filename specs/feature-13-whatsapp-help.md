# Spec 13: Chat with TutorLink on WhatsApp

Status: **approved** (2026-10-16), requested by the owner.
Adds to spec 6 (feedback and the help assistant).

## Why

Many parents and tutors would rather message on WhatsApp than fill in a form. TutorLink has a WhatsApp Business
number; the help desk should offer it.

## Requirements

### R1. The WhatsApp button
1. Help & feedback (parents and tutors) shows "Prefer WhatsApp?" with a **Chat with us on WhatsApp** button, and
   the help chat shows **Talk to a person on WhatsApp** under its disclaimer.
2. Both open a WhatsApp chat with TutorLink's number (`wa.me`), with a message already started that says who is
   writing: their role, name and account email ("Hi TutorLink, I'm a parent, Ada Okafor (ada@example.com). I need
   help with: "). Nothing is sent until they press send in WhatsApp.
3. The number is a site setting (`NEXT_PUBLIC_SUPPORT_WHATSAPP`, international digits); while it's empty, the
   buttons are hidden.
4. Admins answer from TutorLink's WhatsApp Business app; nothing is stored in TutorLink.

## Non-goals
- The WhatsApp Business Platform (Meta's API): messages in /admin, replies from /admin, or the help assistant
  answering on WhatsApp. These need Meta approval and can come later.

## Acceptance criteria
- [x] R1: with the setting, both buttons open wa.me with the number and a message naming the role, name and email; without it they're hidden.
