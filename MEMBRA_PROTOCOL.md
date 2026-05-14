# MEMBRA Protocol

Membra_api is the system of record.

This repo follows the shared Membra protocol for proof review, creative moderation, fraud review, dispute handling, and payout approval queues.

Core rule: admins review derived records but do not create conflicting campaign, owner, asset, placement, proof, or payout state outside the API.

Shared IDs: own_, adv_, ast_, cmp_, crt_, plc_, kit_, proof_, scan_, tap_, pay_, pout_, aud_.

Review states used here: review_pending, approved, rejected, revision_requested, disputed, held, released.
