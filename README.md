# Membra Admin

Membra Admin is the internal operations console for the MEMBRA ecosystem.

It gives operators a controlled place to review campaign creatives, inspect proof submissions, manage media kit status, resolve claims, monitor vendor orders, and check reward readiness.

## One-line thesis

Membra Admin turns MEMBRA from a marketplace idea into an operable network with review queues, status gates, audit trails, and release controls.

## Role in the ecosystem

- `Membra_api` owns source-of-truth records.
- `Membra_ads` defines the physical ad network workflows.
- `Membra_mobile` submits owner proof records.
- `Membra_proofbook` records proof hashes and audit entries.
- `Membra_wallet` controls payment and reward state.
- `Membra_vendor_adapters` updates kit and vendor status.

## Admin modules

- creative review
- asset verification
- proof review
- media kit status
- vendor order status
- claim handling
- campaign status
- reward readiness
- audit timeline
- operator notes

## Core queues

- creatives needing review
- assets needing verification
- proofs needing review
- kits needing action
- claims needing resolution
- rewards needing release check

## Operator rule

No campaign placement becomes active until creative, kit identity, and required proof gates pass.

No reward release becomes ready until the proof state and payment state agree.

## Current stage

Operations-console scaffold. Next step is a lightweight FastAPI or React admin dashboard connected to `Membra_api`.
