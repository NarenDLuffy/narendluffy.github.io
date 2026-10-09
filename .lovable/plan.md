# Remove test employees from the "trial" company code

## What I found

Under the "trial" company code there is leftover test data from earlier checks:

- **Checked-in people (4):** Test1, Test3, Test5, test6 — still showing as present in rooms
- **Notification registrations (2):** devices belonging to Test5 and test6
- **Old alerts (3):** already expired, but still stored

## What I'll do

Delete, for the "trial" company code only:

1. All 4 test check-ins, so the rooms and Company page no longer show them
2. The 2 test notification registrations, so those devices stop receiving alerts for "trial"
3. The 3 expired test alerts, to clean up fully

No app code changes needed — this is a data cleanup only. Real colleagues using other company codes are untouched.

## Technical details

- Rows are matched by the hashed key of the normalized code "trial" (`ran1live:trial` → SHA-256), the same way the app stores them.
- Deletes run on `company_presence`, `push_subscriptions`, and `company_alerts` via the database tool (approval may be requested for the deletes).
