# Consensus

One round, one question, and a validator that can reject a well-formed lie.

## The nondeterministic calls

There are exactly three nondeterministic operations in the contract, and
all three happen inside one round:

| Call | Where | What enters | What comes back | Why code cannot do it |
|---|---|---|---|---|
| `gl.nondet.web.get(policy_url)` | `_fetch_doc` | the clause set's committed location | status and bytes | the policy document is off chain; a contract cannot hold every wording |
| `gl.nondet.web.get(notice_url)` | `_fetch_doc` | the review's committed location | status and bytes | same, for the notice under review |
| `gl.nondet.exec_prompt(..., response_format="json")` | `_node_round` | a JSON envelope: the notice excerpt, and per ground the cited label, the asserted ground and a window of the policy around that label | one row per ground: `clause_located`, `clause_quote`, `ground_stated_in_notice`, `notice_quote`, `supported`, `scope_exceeded`, `basis` | whether a clause as written reaches a stated ground is reading, not arithmetic |

Both fetches are hashed before anything reads them. Bytes whose sha256 does
not match the committed digest are never decoded, never excerpted and never
shown to a model.

## What the leader does

`_node_round(ctx)`, in order:

1. fetch the policy document, hash it, cap it, decode it;
2. fetch the notice document, hash it, cap it, decode it;
3. if either is not `EXAMINED`, stop: the panel is not convened and every
   row is `UNDECIDED`;
4. count, **in code**, how many markers of text addressed to a reader the
   notice carries;
5. compute, **in code**, two triage bits per ground: does the cited clause
   label literally occur in the policy bytes, and does the asserted ground
   literally occur in the notice bytes;
6. build the panel envelope, with a deterministic window of the policy
   around each cited label;
7. call the panel once, with `response_format="json"`;
8. read the answer strictly - one row per ground, exact types, known enum
   values, bounded strings - and fail closed to `INVALID` on anything else;
9. hold every positive answer to the bytes this node verified: an
   ungrounded `clause_located` becomes not located, an ungrounded
   `ground_stated_in_notice` becomes not stated, and the quote is dropped;
10. derive each row's outcome **in code** from the grounded fields;
11. return the payload, canonically serialised.

The leader returns the canonical JSON of that payload. It does not return a
verdict: no node names the verdict.

## What each validator does

`_validator_decision(leader_res, reproduce, ctx)`:

1. run `_node_round(ctx)` **itself**, from its own fetches and its own
   panel call. The reproduction never reads anything the leader said;
2. parse the leader's payload with `_parse_payload`, which checks, with no
   trust at all:
   - the schema, the review id, the round number and the definition hash
     against the contract's own state;
   - both document digests against the ones the review is bound to;
   - that every status, panel state and outcome is a known value;
   - that the directed-text count is an integer in range;
   - that the panel state is consistent with the document statuses;
   - that one row exists per ground, in index order, with no duplicate
     index, and each row's `clause_ref` is the one the review recorded;
   - that every boolean is a boolean (`isinstance(True, int)` is true in
     Python, so booleans are checked for exactly);
   - that each row's `outcome` is the one `_ground_outcome` derives from
     that same row - a leader cannot name an outcome its own fields do not
     support;
   - that on a round where the panel did not answer, every row is exactly
     the shape an unread round is allowed to have;
   - **that every quote in the payload occurs in the bytes this validator
     fetched and hashed itself.**
3. compare the decision fields with `_first_difference`.

Any failure in step 2 or any difference in step 3 is a disagreement, and an
exception inside the validator propagates, which also counts as one.

## Equivalence: what must match, what may differ

Must match - these are the fields that decide the verdict or that a
consumer reads:

```
schema, review_id, round, definition_hash
policy_sha256, notice_sha256
policy_status, notice_status
directed_text_hits
panel_state
per ground: clause_ref, clause_located, ground_stated_in_notice,
            supported, scope_exceeded, outcome
per ground: clause_ref_literal, assertion_literal
```

May differ - two honest validators can produce these differently without
disagreeing about anything that matters:

```
basis            (one sentence of reasoning, diagnostic only)
which grounded span was chosen as clause_quote or notice_quote
```

A quote may differ, but every quote must be **grounded**. The rule is "a
span of the document this node verified", not "the same span the leader
picked". Requiring identical spans would make honest validators disagree
over nothing; requiring no span at all would let a leader invent language.

Not equivalent, ever:

```
SUPPORTED vs UNSUPPORTED
located vs not located
stated vs not stated
EXAMINED vs UNAVAILABLE or HASH_MISMATCH
READ vs SKIPPED or INVALID
a directed-text count of 0 vs any count above 0
```

## Forged-leader defence

The validator is a custom `gl.vm.run_nondet_unsafe` validator precisely
because the leader's result is treated as adversarial. These are the attacks
it refuses, each covered by a test in `tests/direct/test_validators.py` that
runs the contract's own validator closure through
`direct_vm.run_validator`:

| A leader that... | is rejected because |
|---|---|
| claims a ground is supported when this node read it as unsupported | the per-ground `supported` and `outcome` fields are compared |
| claims no scope was exceeded when this node saw that it was | `scope_exceeded` is compared |
| claims a clause was located, with a quote that is not in the policy | the quote is checked against this node's own bytes |
| offers policy language as proof of what the notice said | each quote is checked against the document it belongs to |
| names `SUPPORTED` while its own row says `UNCLEAR` | the outcome is re-derived from the row |
| smuggles `1` where a boolean belongs | booleans are checked for exactly |
| smuggles an unknown outcome, status or panel state | every enum must be a known value |
| re-points the payload at another review, round, version or document | all five bindings are checked against state |
| claims the documents were examined when this node cannot fetch them | the document statuses are compared |
| claims a document is unavailable when this node reads it fine | same comparison, in the other direction |
| hides that the notice addresses its reader | the marker count is compared |
| adds a row, drops a row, or repeats an index | the row set must match the review's grounds exactly |
| returns a payload with no findings on a round that did read | an unread round has one allowed shape, and a read round may not use it |
| returns prose, nothing, or a truncated object | the payload must parse into the exact structure |

True-controls are tested alongside: an honest leader is agreed with,
reworded reasoning is agreed with, and a different but grounded quote is
agreed with. Without those, a validator that always said no would look
perfect.

## Leader failures

A leader can fail rather than return. `_vote_on_leader_error` decides what
that is worth:

| Leader error | Validator agrees when |
|---|---|
| `[PANEL] ...` | never. The round can read the documents again; a panel failure is not a fact about the world. |
| `[TRANSIENT] ...` | this node's own run also failed transiently. |
| `[EXPECTED] ...` / anything else prefixed | this node's own run failed with the identical message. |
| unprefixed | never. |

If the validator's own reproduction succeeds, it does not agree that the
work was impossible.

## Failure semantics

| Situation | Result | Terminal? |
|---|---|---|
| a document cannot be fetched, is the wrong bytes, is too large, or is not readable text | `RECORD_UNAVAILABLE` | no, retryable |
| the panel answered unusably | `INCONCLUSIVE` | no, retryable |
| a ground was read but cannot be settled | `INCONCLUSIVE` | no, retryable |
| the retry limit is reached while still unsettled | the same verdict, status `RESOLVED` | yes, and never consumable |
| the notice addresses its reader and every ground otherwise stood | `INCONCLUSIVE` | no, retryable |
| validators disagree | the transaction does not commit a verdict | n/a |

Nothing uncertain becomes positive. `is_consumable` is false for every
retryable state, for a withdrawn review, for a revoked clause version and
for a stale one, which makes the downstream gate fail closed by default.

A protocol-level `UNDETERMINED` transaction is not the contract's
`INCONCLUSIVE`. The first means the network could not decide the
transaction, and no state changed. The second is a recorded reading that
could not settle, and it is stored with the round that produced it.

## Why consensus is load-bearing

Remove consensus and the contract loses the only inputs it cannot compute:
whether the cited clause is in the document at all, and whether the clause
as written reaches the ground the notice gave. Everything else in this
contract is deterministic - and worth nothing without those two facts,
because the entire question is whether a prose reason matches a prose rule.

Remove consensus but keep a single reader, and the contract loses something
different: the ability to tell a true reading from a purchased one. The
validator exists so that the party whose decision is under review cannot be
the party whose reading of it counts.
