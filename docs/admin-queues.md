# Admin Queue Map

Membra Admin is built around review queues and release checks.

## Queue 1: Creative review

Input:
- campaign id
- advertiser id
- creative file
- destination URL
- campaign terms

Output:
- approved
- rejected
- revision requested

## Queue 2: Asset verification

Input:
- owner id
- asset id
- asset type
- location context
- evidence file

Output:
- verified
- needs more evidence
- rejected

## Queue 3: Proof review

Input:
- proof id
- campaign id
- owner id
- asset id
- media kit id
- evidence file
- timestamp

Output:
- approved
- rejected
- disputed

## Queue 4: Kit status

Input:
- media kit id
- vendor
- tracking state
- owner receipt state

Output:
- ordered
- shipped
- delivered
- receipt confirmed
- active

## Queue 5: Reward readiness

Input:
- campaign funding state
- proof review state
- owner payout readiness
- claims state

Output:
- ready
- hold
- blocked
- released

## Admin release rule

Reward release requires funding state, proof state, and claim state to be consistent.
