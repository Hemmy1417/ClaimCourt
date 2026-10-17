# Integration

ClaimCourt is meant to be read by other contracts. A consumer needs no web
access, no prompt, no equivalence principle and no knowledge of how the
round works. It needs one view.

## The smallest possible consumer

```python
# { "Depends": "py-genlayer:<the runner your contract pins>" }

from genlayer import *


@gl.contract_interface
class IClaimCourt:
    class View:
        def is_denial_supported(self, review_id: str, as_of: str) -> bool: ...
        def is_denial_unsupported(self, review_id: str,
                                  as_of: str) -> bool: ...
        def review_outcome(self, review_id: str, as_of: str) -> dict: ...

    class Write:
        pass


COURT = Address("0x0000000000000000000000000000000000000000")  # see README


class DisputedAmountHold(gl.Contract):
    """Releases a held amount only when the refusal that caused the hold was
    reviewed and did not stand."""

    def _review(self, review_id: str, as_of: str) -> dict:
        return IClaimCourt(COURT).view().review_outcome(review_id, as_of)

    @gl.public.write
    def release(self, review_id: str, as_of: str) -> None:
        outcome = self._review(review_id, as_of)
        if not outcome["consumable"]:
            raise gl.vm.UserError(
                "EXPECTED: that review is not settled, is stale, or its "
                "clause version was withdrawn")
        if not outcome["denial_unsupported"]:
            raise gl.vm.UserError(
                "EXPECTED: the refusal was not found unsupported")
        # ... release
```

The one-line version, for a gate that only needs a yes:

```python
if not IClaimCourt(COURT).view().is_denial_supported(review_id, as_of):
    raise gl.vm.UserError("EXPECTED: the refusal has not been upheld")
```

## `as_of`

Every reliance view takes `as_of`, an ISO `yyyy-mm-dd` date. A view cannot
read a transaction clock, so the consumer supplies the date it is deciding
on. Pass the date of your own transaction. A date before the review was
settled, or anything that is not a date, reads as `UNKNOWN` and therefore
not consumable - never as fresh.

## What `review_outcome` returns

```json
{
  "review_id": "rv-1",
  "clause_set_id": "cs-1",
  "version": 1,
  "definition_hash": "73fe67...",
  "is_current_version": true,
  "status": "RESOLVED",
  "verdict": "DENIAL_UNSUPPORTED",
  "grounds_total": 1,
  "grounds_supported": 0,
  "grounds_failing": 1,
  "directed_text_hits": 0,
  "rounds_used": 1,
  "freshness": "RELIABLE",
  "consumable": true,
  "denial_supported": false,
  "denial_unsupported": true
}
```

### Reading the verdict

| Verdict | What a consumer should conclude |
|---|---|
| `DENIAL_SUPPORTED` | every stated ground stands up against the clause it cites, as written |
| `DENIAL_UNSUPPORTED` | at least one ground is not reached by the clause it cites |
| `DENIAL_OVERBROAD` | the clause does reach the ground, but the notice applies it wider than the clause's own scope. Both convenience booleans are false: decide deliberately |
| `CLAUSE_MISCITED` | a cited clause is not in the bound version of the wording |
| `GROUNDS_MISSTATED` | the notice does not state a ground the review asserted. This is the opener's error, not the decider's |
| `INCONCLUSIVE` | read, not settled. Never act on it |
| `RECORD_UNAVAILABLE` | a bound document could not be examined. Never act on it |
| `WITHDRAWN` | the opener took the review back before it settled |
| `PENDING` | not yet read |

The three verdicts a gate should treat as "no answer" - `INCONCLUSIVE`,
`RECORD_UNAVAILABLE`, `WITHDRAWN` - are kept apart on purpose, and
`consumable` is false for all of them, so a consumer that only checks
`consumable` is already safe.

### Checking the rule the verdict was read against

A consumer that expects a particular wording should pin it:

```python
outcome = IClaimCourt(COURT).view().review_outcome(review_id, as_of)
if outcome["definition_hash"] != EXPECTED_DEFINITION_HASH:
    raise gl.vm.UserError("EXPECTED: reviewed against a different wording")
```

`definition_hash` covers the clause set id, the owner, the label, the
version number, the document location and the document digest. A new
version never changes an existing review's hash, so this check answers
exactly one question: *was this verdict produced against the wording I
expected?* `is_current_version` tells you whether a newer version exists.

## The accumulating record

```python
record = IClaimCourt(COURT).view().clause_record(clause_set_id, version,
                                                 "Clause 4.2")
# {"total": 7, "SUPPORTED": 2, "UNSUPPORTED": 4, "OVERBROAD": 1,
#  "CLAUSE_ABSENT": 0, "NOT_IN_NOTICE": 0, "UNDECIDED": 0, ...}
```

Counters move only when a review settles, and only once per review. A
clause whose refusals keep failing review is visible without reading a
single case. `clause_set_record(clause_set_id, version)` gives the same
picture one level up, counted by verdict.

## The full surface

### Writes

| Method | Who | Effect |
|---|---|---|
| `register_clause_set(label, policy_url, policy_sha256, review_window_days)` | anyone; the caller becomes owner | publishes version 1 and returns the clause set id. `0` days means the 365-day default |
| `publish_clause_version(clause_set_id, policy_url, policy_sha256)` | owner | a new version, with its own definition hash. Returns the version number |
| `revoke_clause_version(clause_set_id, version)` | owner | that version's reviews become `BLOCKED` and not consumable |
| `open_review(clause_set_id, notice_url, notice_sha256, claim_reference, clause_refs, ground_texts)` | anyone | binds the active version and both documents. Returns the review id |
| `resolve_review(review_id)` | anyone | one consensus round. Returns the verdict |
| `retry_review(review_id)` | anyone | re-reads the same bound documents, while rounds remain |
| `withdraw_review(review_id)` | the opener | only before settlement; releases the notice digest |
| `supersede_review(prior_review_id, notice_url, notice_sha256, clause_refs, ground_texts)` | anyone | reviews a re-issued notice, with lineage both ways. The prior review is never rewritten |

### Views

`get_config`, `get_clause_set`, `clause_set_head`, `definition_hash`,
`get_review`, `get_grounds`, `get_receipt`, `review_verdict`,
`review_status`, `freshness`, `is_fresh`, `is_consumable`,
`is_denial_supported`, `is_denial_unsupported`, `review_outcome`,
`clause_record`, `clause_set_record`, `list_reviews`, `notice_under_review`,
`get_stats`.

`get_receipt(review_id, round)` returns the ratified payload of that round
as JSON: the document statuses, the marker count, the panel state, the
triage bits and every grounded row. That is the audit trail - what the
validators actually agreed on, not a summary of it.

`list_reviews(clause_set_id, version, offset, limit)` pages, with a limit
capped at 50.

## Lifecycle

```
                     open_review / supersede_review
                                  |
                                  v
                                 OPEN
                                  |
                          resolve_review
                                  |
        +-------------------------+--------------------------+
        |                         |                          |
   RESOLVED                   RETRYABLE                  WITHDRAWN
 DENIAL_SUPPORTED           INCONCLUSIVE               (withdraw_review,
 DENIAL_UNSUPPORTED         RECORD_UNAVAILABLE          before settlement)
 DENIAL_OVERBROAD                 |
 CLAUSE_MISCITED           retry_review (up to 3 rounds
 GROUNDS_MISSTATED          in total, then RESOLVED
        |                   with the unsettled verdict)
        |
 supersede_review -> a new review against a re-issued notice
```

## What a consumer must not do

- do not read `review_verdict` without `is_consumable` or
  `review_outcome`: a verdict alone says nothing about staleness or
  whether the wording was withdrawn;
- do not treat `DENIAL_UNSUPPORTED` as an instruction to pay a claim. It
  says a reason did not stand, not that the claim is good;
- do not treat `grounds_failing > 0` as the verdict. The precedence rules
  are in the contract, and `verdict` is their output;
- do not re-implement the reading. If you need a different question
  answered, open a review that asks it.
