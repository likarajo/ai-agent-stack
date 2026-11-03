# Login timeout runbook

## Symptoms
- Spinner never stops after SSO redirect
- Hard failure around 30 seconds on slow networks
- Users see "session expired" immediately after a successful login

## Usual causes
1. Auth token refresh takes longer than the client timeout
2. Session cookie `SameSite` / domain mismatch after an SSO redirect
3. Staging rate limits locking shared QA accounts

## Standard fix order
1. Confirm the failure reproduces in an incognito window
2. Check `/health/auth` for token-refresh latency (target under 5s)
3. If latency is high, bump the client login timeout from 30s to 60s temporarily
4. Verify the session cookie domain matches the portal host
5. For QA lockouts, allowlist the staging IP range in the rate limiter
6. File or update an issue with labels `auth` and a severity (`p1`/`p2`/`p3`)

## Severity guide
- **p1**: production login blocked for many users
- **p2**: intermittent or slow-network only
- **p3**: staging / QA inconvenience

## Related past decisions
We keep the public docs and the issue tracker in sync: every auth incident should link this runbook in the issue body.
