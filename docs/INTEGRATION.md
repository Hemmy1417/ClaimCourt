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
        def is_coverage_supported(self, submission_id: str,
                                  as_of: str) -> bool: ...
        def claim_outcome(self, submission_id: str, as_of: str) -> dict: ...
        def get_verdict(self, submission_id: str) -> dict: ...

    class Write:
        pass


COURT = Address("0x0000000000000000000000000000000000000000")  # see README


class ClaimSettlement(gl.Contract):
    """Releases a held amount only when the claim it was held for was
    adjudicated as covered."""

    @gl.public.write
    def release(self, submission_id: str, as_of: str) -> None:
        outcome = IClaimCourt(COURT).view().claim_outcome(submission_id,
                                                          as_of)
        if not outcome["consumable"]:
            raise gl.vm.UserError(
                "EXPECTED: that claim is not settled, is stale, or its "
                "policy version was withdrawn")
        if not outcome["coverage_supported"]:
            raise gl.vm.UserError(
                "EXPECTED: the claim was not adjudicated as covered")
        # ... release
```

The one-line version, for a gate that only needs a yes:

```python
if not IClaimCourt(COURT).view().is_coverage_supported(submission_id, as_of):
    raise gl.vm.UserError("EXPECTED: coverage is not supported")
```

**A verdict is not an instruction to pay.** `COVERAGE_SUPPORTED` says the
conditions were met on the documents reviewed. Authorisation, limits,
finality and the insurer's own rules are the consumer's business, not this
contract's.

## `as_of`

Every reliance view takes `as_of`, an ISO `yyyy-mm-dd` date. A view cannot
read a transaction clock, so the consumer supplies the date it is deciding
on. Pass the date of your own transaction. A date before the claim was
settled, or anything that is not a date, reads as `UNKNOWN` and therefore
not consumable - never as fresh.

## What `claim_outcome` returns

```json
{
  "submission_id": "sub-1",
  "claim_id": "clm-1",
  "policy_id": "pol-1",
  "policy_version": 1,
  "policy_hash": "139d41...",
  "is_current_version": true,
  "status": "RESOLVED",
  "verdict": "COVERAGE_SUPPORTED",
  "evidence_status": "EVIDENCE_SUFFICIENT",
  "conditions_met": 3,
  "conditions_not_met": 0,
  "conditions_unclear": 0,
  "trigger_state": "NOT_DECLARED",
  "fraud_finding": "NOT_ASKED",
  "directed_text_hits": 0,
  "rounds_used": 1,
  "freshness": "RELIABLE",
  "consumable": true,
  "coverage_supported": true
}
```

`get_verdict(submission_id)` is the structured adjudication result the brief
describes, including the four criteria:

```json
{
  "verdict": "COVERAGE_SUPPORTED",
  "coverage_conditions_met": true,
  "exclusion_applies": false,
  "evidence_status": "EVIDENCE_SUFFICIENT",
  "criteria": {
    "policy_version_verified": true,
    "covered_event_supported": true,
    "required_conditions_met": true,
    "exclusion_evidence_found": false
  },
  "evidence_refs": ["E1", "E2"],
  "bounded_reason": "",
  "policy_version": 1,
  "policy_hash": "139d41...",
  "trigger_state": "NOT_DECLARED",
  "fraud_finding": "NOT_ASKED"
}
```

### Reading the verdict

| Verdict | What a consumer should conclude |
|---|---|
| `COVERAGE_SUPPORTED` | every coverage condition was met on this evidence, no exclusion was evidenced, and any declared trigger fired |
| `COVERAGE_NOT_ESTABLISHED` | a condition was positively not met, or a declared trigger did not fire. Not a finding that the claim is false |
| `EXCLUSION_APPLIES` | an exclusion was evidenced, with the words it rests on stored alongside |
| `FRAUD_INDICATORS_FOUND` | the policy asked a bounded fraud question and the documents answer it, with a quote. Indicators, not a determination |
| `INCONCLUSIVE` | read, not settled. Never act on it |
| `EVIDENCE_UNAVAILABLE` | the policy document or a required kind could not be examined. Never act on it |
| `CANCELLED` | the claimant withdrew the claim before it settled |
| `PENDING` | not yet adjudicated |

`INCONCLUSIVE`, `EVIDENCE_UNAVAILABLE`, `CANCELLED` and `PENDING` are all
non-consumable, so a consumer that only checks `consumable` is already safe.

### Checking the policy a verdict was read against

A consumer that expects particular terms should pin them:

```python
outcome = IClaimCourt(COURT).view().claim_outcome(submission_id, as_of)
if outcome["policy_hash"] != EXPECTED_POLICY_HASH:
    raise gl.vm.UserError("EXPECTED: adjudicated under different terms")
```

`policy_hash` covers the policy id, the owner, the version number, the
wording document's location and digest, every coverage condition, every
exclusion, the fraud question, the trigger and the freshness window. A new
version never changes an existing claim's hash, so this check answers
exactly one question: *was this verdict produced under the terms I expected?*
`is_current_version` tells you whether a newer version exists.

## The accumulating record

```python
record = IClaimCourt(COURT).view().policy_record(policy_id, version)
# {"total": 9, "COVERAGE_SUPPORTED": 4, "COVERAGE_NOT_ESTABLISHED": 2,
#  "EXCLUSION_APPLIES": 1, "FRAUD_INDICATORS_FOUND": 0,
#  "INCONCLUSIVE": 2, "EVIDENCE_UNAVAILABLE": 0, ...}
```

Counters move only when a claim settles, and only once per claim. How often
a policy version's claims end up unsettled is as useful a signal as how
often they are paid.

## The full surface

### Writes

| Method | Who | Effect |
|---|---|---|
| `register_policy(policy_url, policy_sha256, coverage_type, definition_json)` | anyone; the caller becomes owner | publishes version 1 with its conditions, exclusions, optional fraud question and optional trigger. Returns the policy id |
| `publish_policy_version(policy_id, policy_url, policy_sha256, definition_json)` | the owner | a new version with its own policy hash; submitted claims keep theirs |
| `revoke_policy_version(policy_id, version)` | the owner | that version's claims stop being consumable, keeping their verdicts |
| `open_claim_challenge(policy_id, decision_question, required_evidence_json, claim_deadline)` | the owner | the bounded question, the kinds of evidence a claim must carry, and the deadline. Returns the claim id |
| `cancel_claim_challenge(claim_id)` | the owner | closes it to new submissions |
| `submit_claim(claim_id, claimant_reference, incident_json, evidence_json)` | anyone | binds the policy version, its hash and every document by sha256. Returns the submission id |
| `resolve_submission(submission_id)` | anyone | one consensus round. Returns the verdict |
| `retry_submission(submission_id)` | anyone | re-reads the same bound documents, while rounds remain |
| `cancel_submission(submission_id)` | the claimant | only before settlement |

### The policy definition

`definition_json` is strict, and anything malformed is refused at
registration rather than at adjudication:

```json
{
  "coverage_conditions": [
    {"ref": "C1", "covered_event": true, "text": "..."},
    {"ref": "C2", "text": "..."}
  ],
  "exclusions": [{"ref": "X1", "text": "..."}],
  "fraud_question": "",
  "review_window_days": 365,
  "trigger": {
    "measure": "cumulative rainfall at the named station",
    "unit": "millimetres",
    "rule": "AT_MOST",
    "threshold": 220,
    "window_start": "2026-06-01",
    "window_end": "2026-09-30"
  }
}
```

`covered_event` marks the conditions that decide whether a covered event
happened at all, which is what `covered_event_supported` reports. `trigger`
and `fraud_question` are optional; omit them and the contract will refuse
any answer to them.

### Views

`get_config`, `get_policy`, `get_claim`, `get_claim_status`,
`get_policy_hash`, `get_policy_version`, `get_submission`, `get_verdict`,
`get_evidence_status`, `get_findings`, `get_receipt`,
`is_coverage_supported`, `freshness`, `is_fresh`, `is_consumable`,
`claim_outcome`, `policy_record`, `list_submissions`, `evidence_first_seen`,
`get_stats`.

`get_receipt(submission_id, round)` returns the ratified payload of that
round as JSON: the document rows, the marker count, the panel state, every
grounded finding, the measurement, the criteria and the verdict. That is the
audit trail - what the validators agreed on, not a summary of it.

`evidence_first_seen(sha256)` names the submission that first committed a
document with those bytes. A document reused across claims is a fact a
reviewer may want; it is never on its own a finding.

## Lifecycle

```text
          register_policy ──> publish_policy_version ──> revoke_policy_version
                 │
          open_claim_challenge ──> cancel_claim_challenge
                 │
            submit_claim
                 │
                 v
              PENDING
                 │
         resolve_submission
                 │
     ┌───────────┼────────────────┐
     │           │                │
 RESOLVED    RETRYABLE        CANCELLED
 COVERAGE_SUPPORTED        INCONCLUSIVE      (cancel_submission,
 COVERAGE_NOT_ESTABLISHED  EVIDENCE_         before settlement)
 EXCLUSION_APPLIES         UNAVAILABLE
 FRAUD_INDICATORS_FOUND         │
                          retry_submission, 3 rounds in total,
                          then RESOLVED with the unsettled verdict
```

## What a consumer must not do

- do not read `verdict` without `consumable`: a verdict alone says nothing
  about staleness or whether the policy version was withdrawn;
- do not treat `COVERAGE_SUPPORTED` as an authorisation to pay;
- do not treat `COVERAGE_NOT_ESTABLISHED` as a finding of fraud - the
  contract keeps those apart on purpose, and so should you;
- do not treat `conditions_not_met` as the verdict. The precedence rules are
  in the contract, and `verdict` is their output;
- do not re-implement the reading. If you need a different question
  answered, publish a policy version that asks it.
