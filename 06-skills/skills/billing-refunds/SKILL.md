---
name: billing-refunds
description: Handle billing disputes, invoice corrections, and refund requests for Northwind portal charges.
---

# Billing refunds skill

## When to activate
- User asks about billing, invoices, charges, refunds, or payment disputes
- Not for login / SSO / password problems

## Steps
1. Identify the invoice or charge the user mentions.
2. Search open issues labeled `billing` for a matching report.
3. If a refund is warranted, draft the refund request fields (amount, reason, invoice id).
4. Summarize next steps for finance — do not silently issue credits.

## Rules
- Cite issue ids when referring to tracker items
- Login failures belong to the login-reset skill, not this one
