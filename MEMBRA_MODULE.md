# MEMBRA Module Contract — Admin

## Role

Operator console for MEMBRA proof review, campaign approval, fraud holds, payout holds, risk notes, and admin decisions.

## System inputs

- review queue items
- proof IDs
- campaign IDs
- payout IDs
- relay IDs
- operator decisions

## System outputs

- admin decisions
- audit events
- fraud holds
- payout holds
- approval/rejection states

## Health

```text
GET /api/health
```

## Replit role

`service`

Runs as the operator/risk console for the MEMBRA OS workspace.

## Production boundary

Admin decisions gate eligibility and visibility. They do not settle funds.
