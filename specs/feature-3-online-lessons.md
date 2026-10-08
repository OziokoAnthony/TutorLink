# Spec 3 of 4: Online and offline lessons, lesson recordings

Status: **approved** (2026-10-07)
Depends on: [1 Bookings and payments](feature-1-bookings-and-payments.md)

## Why

Parents choose between home (offline) and online tutoring. For online lessons, the tutor must upload the
lesson recording with their report, so the parent can check the lesson really happened before the tutor is paid.

## Requirements

### R1. Lesson mode
1. Every booking and job has a mode: `online` or `offline`.
2. **Offline**: the tutor sees the parent's address only once the first period is paid.
3. **Online**: the tutor sets a meeting link (https URL, e.g. Google Meet or Zoom) on the booking. The parent sees it once the first period is paid.
4. When booking or posting an online lesson, the parent must tick a consent: "Lessons will be recorded and kept for review." The booking can't be created without it. The time and text of the consent are stored.

### R2. Recordings
1. A tutor's report for an **online** lesson (due within 24 hours, spec 1 R4.2) can't be submitted until a recording upload has completed for that lesson. This is a 422 with a clear message.
2. Uploads go from the browser **directly to Cloudflare R2** using a short-lived upload URL from the backend. Video never passes through the API server.
3. Allowed: MP4, WebM or MOV, at most **2 GB**. Type and size are checked when the upload URL is issued, and again from R2's stored object before the report is accepted.
4. Recordings are private. The lesson's parent, its tutor and admins can watch it through a viewing link that expires after **15 minutes**. Nobody else can get a link (403).
5. The parent's lesson page shows the recording next to the report, so they can watch it within the 24-hour problem window (spec 1 R5).
6. Recordings are deleted **90 days** after the lesson. They're kept longer while a problem report on that lesson is open.

### R3. Offline report
An offline lesson's report has no recording requirement. It is topic covered plus homework, as today.

## Non-goals
- Hosting live video calls inside TutorLink.
- Transcoding, thumbnails or adaptive streaming. The recording is played as uploaded.
- Recording offline lessons.

## Acceptance criteria
- [ ] An online lesson report without a completed recording returns 422. With one, it succeeds.
- [ ] An upload URL request for a 3 GB file or a `.exe` is rejected.
- [ ] A viewing link is returned to the lesson's parent, its tutor and an admin, and returns 403 for any other parent or tutor.
- [ ] Viewing links are issued with a 15-minute expiry.
- [ ] The tutor gets the address (offline) or the parent gets the meeting link (online) only after the first payment.
- [ ] Recordings older than 90 days with no open problem are deleted by the cleanup job.
- [ ] An online booking request without recording consent is rejected.

## Assumptions
- A Cloudflare R2 bucket and API token are provided. Until then, tests use a fake storage backend.
