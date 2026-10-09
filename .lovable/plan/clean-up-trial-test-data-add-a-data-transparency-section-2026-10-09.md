# Clean up "trial" test data + add a data-transparency section

## 1. Remove test employees from the "trial" company code

Leftover test data found under "trial":

- **Checked-in people (4):** Test1, Test3, Test5, test6 — still showing as present in rooms
- **Notification registrations (2):** devices belonging to Test5 and test6
- **Old alerts (3):** already expired, but still stored

Delete, for the "trial" company code only:

1. All 4 test check-ins, so rooms and the Company page no longer show them
2. The 2 test notification registrations, so those devices stop receiving alerts for "trial"
3. The 3 expired test alerts, to clean up fully

Real colleagues using other company codes are untouched.

## 2. Add "What this app stores" to the How to Use page

A new transparency section on the How to Use page explaining, in plain language:

- **Your name and room check-ins** — stored so colleagues can see who is where; check-ins expire automatically after 2 hours without activity
- **Your company code** — never stored as text; only a one-way scrambled (hashed) version, so even a database leak can't reveal it
- **Notification registrations** — per device: a unique push address from the browser plus two encryption keys used to deliver alerts. No device model, browser, operating system, or location is stored
- **Colleague-needed alerts** — stored for 10 minutes, then gone
- **Nothing else** — no accounts, no passwords, no tracking, no analytics on individuals

## Technical details

- Deletes matched by the hashed key of normalized code "trial" (`ran1live:trial` → SHA-256) on `company_presence`, `push_subscriptions`, `company_alerts` (delete approval may be requested).
- The transparency section is a new block in `src/routes/help.tsx`, matching the existing card style.
- Publish afterwards so the How to Use page update goes live.
