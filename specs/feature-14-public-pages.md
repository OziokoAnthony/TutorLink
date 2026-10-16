# Spec 14: Public subject pages, real numbers, reviews and a price guide

Status: **approved** (2026-10-16), requested by the owner, after comparing with educere.com.ng.

## Why

Parents find tutors through Google ("WAEC Mathematics tutor"), and decide whether to sign up from what they see
before an account: how many tutors there are, what it costs, what other parents say. Today TutorLink's only public
pages are the home page and the legal pages, so search engines find nothing and visitors see no numbers.

## Requirements

### R1. What stays private
1. Visitors still never see a tutor: no name, photo, profile, area or individual offer (as today). Public pages
   show counts, price ranges and reviews only, and send visitors to sign up to see and book tutors.
2. Only tutors parents can book count: approved, account open, and within the NIN deadline (spec 11).

### R2. Real numbers
1. The home page shows, from the database: verified tutors, lessons taught (completed), and the average rating
   with the number of ratings.

### R3. Reviews
1. Public pages show parents' reviews with **the parent's first name, the stars and the comment** only: no surname,
   photo, area, or tutor. Only 4- and 5-star reviews with a comment, newest first.
2. The home page shows the latest 6; a subject page shows the latest 6 for tutors who teach that subject.

### R4. Subject pages (`/subjects`, `/subjects/<subject>`)
1. `/subjects` lists every offered subject (spec 7), grouped Nigerian curriculum / International, with the number
   of tutors teaching it.
2. A subject page shows, for each level it's taught at: the number of tutors, and the **price range per lesson
   parents pay** (TutorLink's parent fee included, as in a booking). With fewer than 3 offers at a level, it says
   "Prices vary" instead, so no single tutor's price is exposed.
3. It also shows the subject's reviews (R3.2), the three steps (sign up, choose a tutor, pay and start), and
   "Sign up to see tutors" and "Post a request" buttons, both leading to sign-up.
4. A subject with no tutors yet says so and invites a request.

### R5. Level pages (`/levels/<level>`)
1. One page per level (primary, junior secondary, senior secondary, international): each subject taught at that
   level with its tutor count and price range (R4.2).

### R6. Search engines
1. Every public page has its own title and description, e.g. "Mathematics tutors in Nigeria | TutorLink".
2. A `sitemap.xml` lists the home page, `/subjects`, every subject and level page, and the legal pages; `robots.txt`
   allows them and keeps `/dashboard`, `/admin` and `/receipts` out.
3. Text is written for parents, not stuffed with keywords; numbers on the pages are real.
4. Pages are cached for an hour, so a sleeping API doesn't slow every visit.

## Non-goals
- City or area pages (tutors' areas are free text; to revisit when there are enough tutors per city).
- A blog, or showing any tutor publicly.

## Acceptance criteria
- [x] R1: no public response contains a tutor's name, photo, area, id or a single offer; tutors who aren't approved, are removed or are past the NIN deadline aren't counted.
- [x] R2: the stats match the database.
- [x] R3: public reviews carry only first name, stars and comment; 1-3 star reviews and reviews without a comment are left out.
- [x] R4, R5: subject and level pages give per-level tutor counts and parent price ranges (fee included), "Prices vary" under 3 offers, and only offered subjects.
- [x] R6: each page has its own title; the sitemap lists every subject and level page; robots.txt keeps private areas out.
