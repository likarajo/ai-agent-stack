# Auth design notes (northwind-portal)

## Login flow
1. User opens `/login`
2. Portal redirects to the IdP
3. IdP posts back with an authorization code
4. Portal exchanges the code for tokens and sets a session cookie
5. Browser lands on `/app`

## Timeouts
The browser client historically used a 30s hard timeout around step 4.
On constrained mobile networks the token exchange can exceed 30s, which looks like a hung login.

## Cookie rules
After issue #89 the session cookie uses `SameSite=Lax` and must be scoped to the portal apex domain.
A wrong domain produces a spinner that never completes even though the IdP succeeded.

## Agent-friendly tip
When someone asks "how do we usually fix login timeouts?", start from the login-timeout runbook, then search open issues mentioning login.
