---
name: login-reset
description: Reset or unlock a portal login when a user cannot sign in after SSO or password failures.
---

# Login reset skill

## When to activate
- User cannot log in, needs a password reset, or is locked out after SSO
- Auth / login access problems (not billing or invoicing)

## Steps
1. Confirm whether the failure is password, SSO redirect, or account lockout.
2. Search open issues mentioning login for a known incident.
3. If it matches the login-timeout runbook, follow that fix order first.
4. Otherwise guide a password reset and verify `/login` afterwards.

## Rules
- Do not invent account state — only use tool/API results
- Billing and invoice questions belong to the billing-refunds skill, not this one
