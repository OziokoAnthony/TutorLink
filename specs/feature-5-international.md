# Spec 5 of 5: International parents and tutors (location and currency)

Status: **draft** (2026-10-08), awaiting approval
Depends on: [1 Bookings and payments](feature-1-bookings-and-payments.md) (balance, dedicated accounts, payouts), [2 Job posts](feature-2-job-posts.md) (job visibility), [3 Online lessons](feature-3-online-lessons.md) (online mode)

## Why

TutorLink is built for Nigeria today: every amount is in naira and every payment goes through a Paystack naira
account. The business wants to serve parents and tutors in other countries too. Naira stays Nigeria-only, everyone
else pays in US dollars, and payments are still by bank transfer to the parent's own account number, never by card.

## Terms

- **Location**: the country a user picks at registration.
- **Currency**: set by location. Nigeria → **NGN**. Every other country → **USD**.
- **Cross-border**: a booking or job where the parent and the tutor are in different countries.

## Requirements

### R1. Location
1. Registration asks parents and tutors for their country (required, from a fixed list of countries).
2. Users can't change their own country. An admin can change it, with a note, only while the user has no accepted or active booking and a zero balance.
3. Existing users get Nigeria when this ships.
4. Admins have no location.

### R2. Currency
1. A user's currency comes from their location: NGN for Nigeria, USD everywhere else. Only Nigerian users ever pay, price or are shown amounts in NGN.
2. Every amount is stored with its currency, and no two currencies are ever added together. USD amounts are rounded to cents, NGN amounts to kobo.
3. A tutor prices their offers in their own currency.
4. A parent posts a job (spec 2) with a price in their own currency.
5. A booking's currency is the parent's currency. Its P, parent price and periods are in that currency. The fee rates S% and T% are the same in every currency (spec 1 R1).

### R3. Paying: one account number per parent, no cards
1. No card payments, anywhere, in any currency (as spec 1).
2. Each parent has one dedicated account number in their currency, created the first time a booking of theirs is accepted (spec 1 R3.1) and always shown on their dashboard:
   - **Nigeria (NGN)**: a Paystack Dedicated Virtual Account, as built in spec 1.
   - **Other countries (USD)**: a USD account number from a second provider (open question 1).
3. No two parents ever have the same account number. The database enforces this per provider.
4. A parent's balance is in their currency. Deposits, lesson payments, refunds and withdrawals all use it, with the same ledger rules as spec 1 R3.4. A deposit in any other currency isn't credited: it's flagged to the admin to return.
5. Deposit webhooks from the second provider follow the same rules as Paystack's: valid signature, processed once, re-verified with the provider before crediting.

### R4. Who sees which jobs
1. A tutor in Nigeria sees open jobs from parents in every country (spec 2 R2.2).
2. A tutor outside Nigeria never sees jobs from parents in Nigeria: they're left out of the job list, and opening or applying to one by id is a 404.
3. All other spec 2 visibility rules still apply.

### R5. Cross-border lessons are online only
1. A cross-border booking request or job application is allowed only for online lessons (spec 3). An offline one is a 422.
2. A job from abroad that is offline is shown only to tutors in the parent's country.

### R6. Tutor payouts
1. Tutors in Nigeria are paid in NGN to their Nigerian bank account (spec 1 R6). Earnings from USD bookings are converted to NGN at payout. The rate used and the NGN amount are recorded on the payout, and the tutor sees both.
2. Tutors outside Nigeria are paid in USD through the second provider.
3. Exchange-rate differences between payment and payout are TutorLink's gain or loss, shown to the admin per payout.

## Non-goals
- Card payments in any currency.
- Currencies other than NGN and USD.
- Users changing their own country.
- Showing prices to a user in a currency other than their own (no on-screen conversion for parents).

## Acceptance criteria
- [ ] Registration without a country is a 422. A user can't change their country, and an admin can't while the user has an active booking or a balance.
- [ ] A parent in Nigeria gets an NGN Paystack account number, and a parent elsewhere gets a USD one from the second provider. Both are on the dashboard.
- [ ] Two parents never get the same account number. A repeated number is refused by the database.
- [ ] A non-Nigerian user can't create, price or pay anything in NGN. A Nigerian parent's booking is in NGN.
- [ ] A USD deposit to an NGN parent's account, or the reverse, isn't credited and is flagged to the admin.
- [ ] A tutor outside Nigeria doesn't see Nigerian jobs in the list and gets 404 opening or applying to one. A Nigerian tutor sees jobs from every country.
- [ ] An offline cross-border booking request or application is a 422.
- [ ] A Nigerian tutor's earning from a USD booking is paid in NGN, and the payout records the rate and both amounts.
- [ ] The balance equals the sum of ledger entries, per parent, in their one currency, after every operation tested.
- [ ] No API response sums amounts of different currencies.

## Open questions
1. **Second provider for USD account numbers (blocking).** Paystack only issues dedicated accounts in naira. One option is Stripe's bank-transfer payments, which give each customer their own USD account number. We need to confirm that Stripe can serve a business registered in Nigeria; if not, we compare other providers. Default: research providers before building R3.2.
2. **A parent abroad booking a Nigerian tutor's offer.** The offer is priced in NGN but the parent pays in USD. Default: the tutor sets an optional USD price on each offer, and only offers with a USD price can be booked from abroad.
3. **Which tutors parents see in `/tutors`.** Default: parents in every country see tutors from every country. Cross-border bookings are online only (R5).
4. **Exchange rate at payout.** Default: the admin enters the rate when paying, and the app suggests the provider's current rate.

## Assumptions
- Spec 1 is built, and specs 2 and 3 are built before R4 and R5.
- The second provider can pay out USD to tutors abroad (R6.2), or USD payouts are marked as paid manually until it can.
