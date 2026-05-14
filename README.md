# Membra Admin

**Membra Admin is the internal operations console namespace for MEMBRA Labs and the MEMBRA Proof Network.**

It is responsible for the human/operator control layer behind proof review, creative approval, fraud flags, claims, payout holds, vendor oversight, and campaign status control.

## Company Context

- Company: **MEMBRA Labs**
- Flagship product: **MEMBRA Proof Network**
- Module: **Membra Admin**
- Category: operator console, proof review, creative approval, payout oversight, fraud operations

## One-Line Thesis

Membra Admin turns MEMBRA from a marketplace idea into an operable proof network with review queues, status gates, audit trails, and release controls.

## Product Role

Membra Admin is the control room for the proof-commerce workflow.

It should manage:

- creative approval
- owner verification status
- asset verification status
- proof review queues
- proof approval/rejection/dispute decisions
- fraud flags
- campaign status
- media-kit status
- vendor order status
- payout hold/release review
- claims and dispute handling
- audit log review

## Core Workflow

1. Advertiser submits campaign and creative.
2. Admin approves or rejects creative.
3. Owner submits asset or surface.
4. Admin verifies asset where required.
5. Media kit is generated.
6. Owner submits proof.
7. Admin reviews proof.
8. Approved proof unlocks payout eligibility.
9. Disputed proof creates claim workflow.
10. All state changes create audit records.

## Integration Points

| Repo | Integration |
|---|---|
| `overandor/Membra_ads` | campaign, asset, media-kit, proof, scan, audit records |
| `overandor/Membra_wallet` | payout eligibility, holds, releases, failed payouts |
| `overandor/Membra_proofbook` | proof hashes and audit trail verification |
| `overandor/Membra_vendor_adapters` | vendor order status and exception handling |
| `overandor/membra-qr-gateway` | dashboard views that can surface admin-reviewed states |
| `overandor/Membra_kpi` | operations scorecards and proof review metrics |

## Required Admin States

Proof states:

- `submitted`
- `approved`
- `rejected`
- `disputed`
- `needs_more_evidence`

Payout states:

- `pending`
- `eligible`
- `held`
- `released`
- `failed`
- `reversed`

Campaign states:

- `draft`
- `creative_review`
- `approved`
- `funded`
- `active`
- `paused`
- `complete`
- `cancelled`

## Safety Rules

- no payout release without approved proof
- no creative activation without review
- no manual override without audit record
- no public exposure of sensitive owner, payment, or identity data
- no deletion of fraud or dispute evidence without retention policy
- no unsupported income or performance claims

## Productization Priority

This repo should receive the first internal operator UI after `Membra_ads` and `membra-qr-gateway` are demo-connected.

## Current Stage

Operations-console scaffold. Next step is a lightweight FastAPI or React admin dashboard connected to `Membra_ads` / `Membra_api`.