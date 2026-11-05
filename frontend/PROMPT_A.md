## Context
RepairBuddy frontend: React 19 + Vite + Tailwind + zustand (this folder, code in src/). Firebase phone auth already exists (src/lib/firebase.js, AuthPage requestPhoneOtp/confirmPhoneOtp, authStore loginAsCustomer/loginAsWorker/loginAsAdmin). The backend verifies Firebase ID tokens. POST /customers/register and POST /workers/register take the uid from the token and return 409 if the user already exists. Admin access exists only through a Firebase custom claim.

Current problems:
- authStore generates uids in the browser (`cust_${Date.now()}`, `worker_${Date.now()}`) and calls register on EVERY login, so returning users hit a 409 error.
- The "Administrator Console" button on AuthPage calls loginAsAdmin() with a hardcoded `admin_user` and no authentication.

## Task
Fix 1: make login use the real Firebase uid and handle returning users correctly. Fix 2: replace the hardcoded admin login with a real Firebase login gated by the admin claim.

## Constraints
- Touch only src/. No new dependencies. Keep existing api function names and the mock-mode flow working (mock mode may keep its own fake users).
- The admin claim name must live in ONE constant. Ask the user (Varun) for the exact claim name from the backend scripts/set_admin.py before relying on it. Do not guess.
- If the backend has a "get my profile" endpoint, use it. If not, treat a 409 on register as "already registered" and load the profile with api.getWorker(uid) for workers; for customers reuse the data returned or cached. Report which path you used.
- Retry only network/5xx errors; show 4xx errors immediately in a toast.
- Do not commit .env. Do not push. Commit locally only, one commit per fix.

## Success Criteria
Fix 1:
- No uid is generated in the browser: `grep -n "Date.now" src/store/authStore.js` shows no uid creation.
- A new user logs in and registers exactly once; a returning user (register returns 409) logs in with no error toast and lands on the right home page.
- If an existing account has a different role than the one chosen at login, show a clear message and do not switch the role.
- Logging out and logging back in as the same user works without errors.
Fix 2:
- The Administrator Console button no longer calls a hardcoded admin login. It uses the same Firebase phone login.
- After login, /admin is reachable only when the token claim says admin; otherwise redirect with a message.
- `grep -rn "admin_user" src` outside mockStore/mockData returns nothing.
- ProtectedRoute decides roles from the authenticated state, not only from localStorage.
- `npm run build` and `npm run lint` pass.

## Output
- Diff plus a list of files changed.
- Manual test steps using the Firebase test number +91 9999900001 with code 123456.
- A note on which "get profile" path you used and anything that needs Varun's input.

---

## Execution Loop
Work this task as a refine-and-recheck loop, not a single pass:
1. **Do**: produce the next concrete step.
2. **Check**: compare the result against each line in Success Criteria explicitly; state pass/fail and why.
3. **Revise**: fix what failed. If Context/Constraints turn out wrong or incomplete, update them and note the change.
4. **Repeat** until all criteria pass, or until continuing needs a human decision (admin claim name, missing endpoint, ambiguous requirement) - then stop and ask instead of guessing.
