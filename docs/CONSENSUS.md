# Consensus

One round, one reading, and a validator that can reject a well-formed lie.

## The nondeterministic calls

There are exactly three nondeterministic operations in the contract, and all
three happen inside one round:

| Call | Where | What enters | What comes back | Why code cannot do it |
|---|---|---|---|---|
| `gl.nondet.web.get(policy_url)` | `_fetch_doc` | the policy version's committed location | status and bytes | the wording lives off chain |
| `gl.nondet.web.get(evidence_url)` | `_fetch_doc`, once per document | each committed evidence location | status and bytes | so does the claim file |
| `gl.nondet.exec_prompt(..., response_format="json")` | `_node_round` | a JSON envelope: the policy excerpt, the claim's own declared facts, each coverage condition, each exclusion, an excerpt of every readable document, and - where the policy declares them - the trigger's measure and window and the bounded fraud question | per condition: met / not met / unclear with a quote and the document it came from; per exclusion: evidenced / not evidenced / unclear; whether the evidence is sufficient and whether any two documents contradict; the measured value for a trigger; the answer to the fraud question | whether an assessor's description of layered tide marks is "gradual deterioration", or a door left unlocked is "forcible entry", is reading |

Every document is hashed before anything reads it. Bytes whose sha256 does
not match the commitment are never decoded, never excerpted and never shown
to a model.

## What the leader does

`_node_round(ctx)`, in order:

1. fetch the policy document, hash it, cap it, decode it;
2. fetch every committed evidence document and do the same, recording for
   each a status and, when it failed, why: `FETCH_FAILED`,
   `HASH_MISMATCH`, `TOO_LARGE` or `UNREADABLE`;
3. count, **in code**, how many markers of text addressed to a reader the
   evidence carries;
4. work out, **in code**, which of the kinds the challenge requires are
   actually readable; if any is missing, the panel is not convened at all;
5. convene the panel once, with `response_format="json"`;
6. read the answer strictly - one row per condition and per exclusion, in
   the policy's own order, exact types, known values, bounded strings - and
   fail closed to `INVALID` on anything else;
7. hold every answer to the bytes this node verified: an ungrounded `MET`
   or `NOT_MET` becomes `UNCLEAR`, an ungrounded `EVIDENCED` becomes
   `UNCLEAR`, an ungrounded contradiction is dropped, an ungrounded
   measurement is dropped, and an ungrounded accusation becomes `UNCLEAR`;
8. compare the measurement with the threshold **in code** to get the
   trigger state;
9. derive the four criteria and the verdict **in code**;
10. return the payload, canonically serialised.

The model is never asked for a verdict, a status, a consequence, or whether
a threshold was crossed.

## What each validator does

`_validator_decision(leader_res, reproduce, ctx)`:

1. run `_node_round(ctx)` **itself**, from its own fetches and its own
   panel call. The reproduction never reads anything the leader said;
2. parse the leader's payload with `_parse_payload`, which checks, with no
   trust at all:
   - the schema, the submission and claim ids, the round, the policy hash,
     the policy version, the policy document digest and the evidence digest,
     all against the contract's own state;
   - that every status, reason, finding, panel state and trigger state is a
     known value, and that a status and its reason agree (a reachable
     document has no failure reason, and an unreachable one has one);
   - that the document rows describe the committed documents, in order;
   - that the list of missing required kinds is exactly what those rows
     imply;
   - that the panel was convened only when it was allowed to be;
   - that every boolean is a boolean and every integer an integer in range
     (`isinstance(True, int)` is true in Python, so booleans are checked for
     exactly);
   - that a substantive finding carries a quote, and that only a
     substantive finding carries one;
   - **that every quote occurs in the bytes this validator fetched and
     hashed itself**;
   - that the trigger state is the one the comparison produces;
   - **that the verdict and the four criteria are the ones this payload's
     own findings derive**;
3. compare the decision fields with `_first_difference`.

Any failure in step 2, or any difference in step 3, is a disagreement; an
exception inside the validator propagates and counts as one too.

## Equivalence: what must match, what may differ

Must match - the fields that decide the outcome or that a consumer reads:

```text
schema, submission_id, claim_id, round
policy_hash, policy_version, policy_sha256, evidence_digest
policy_status, policy_reason, missing_required_kinds
directed_text_hits, panel_state, trigger_state
verdict
the four criteria
per document: evidence_id, kind, status, reason, byte_count
the measurement: value_found, value
the order of the conditions and exclusions
```

In one line: **the facts must match, the outcome must match, and the
reasoning may differ.**

May differ - two honest validators can produce these differently without
disagreeing about anything that matters:

```text
the label on an individual condition or exclusion
the fraud finding, where it does not change the verdict
which grounded span was quoted, and from which document
one sentence of reasoning per finding
```

The fraud finding is the one judgement not compared directly, because
every answer to it that changes anything changes the verdict, which is
compared: `INDICATORS_FOUND` produces `FRAUD_INDICATORS_FOUND` and
`UNCLEAR` produces `INCONCLUSIVE`, so a node that disagrees about the
accusation disagrees about the outcome. It is still derived in code from
each node's own findings, the gate refuses a payload whose criteria do not
follow from its findings, and the ratified leader's are what gets stored.

An earlier draft of this document said the four criteria were not compared
either, on the same reasoning. That was wrong about the contract:
`_first_difference` walks `CRITERIA_FIELDS` and compares all four. The
mutation sweep is what caught the error - the mutation that drops the
verdict from the comparison *survived*, because the criteria comparison was
refusing every forged payload before the verdict line was ever reached.
Closing it needed the one forgery that moves the verdict and leaves all
four criteria untouched: a different answer to the fraud question
(`test_only_the_verdict_separates_two_otherwise_identical_readings`). The
same sweep found the matching gap for `policy_reason`, since any change of
`policy_status` moves the verdict too
(`test_nodes_must_agree_on_why_the_policy_could_not_be_read`).

### Why only the outcome is consensus-critical

Two live runs taught this, and both are worth recording.

The **first** required every per-clause label to match. The round came back
**1 agree, 3 disagree** with nothing stored - while the leader receipt still
reported SUCCESS. The validators had read the same documents and reached the
same conclusion about the claim; they had simply labelled a borderline
condition differently (`MET` for one node, `UNCLEAR` for another) on the way
there.

The **second** moved the agreement to the verdict and the four criteria.
Four scenarios then settled, including an exclusion found on an assessor's
own words and a parametric trigger compared in code. The fifth - the claim
whose evidence instructs its reader - came back **0 agree, 3 disagree**: the
criteria are fine-grained enough to split for exactly the same reason the
labels were. A node that read one condition as unclear and a node that read
it as met both reached `INCONCLUSIVE`, and still disagreed about
`required_conditions_met`.

So the agreement is now on the facts and the outcome, and nothing else.

That is honest variation on a semantic question, and a protocol that splits
over it is not safer - it is just unable to decide. So the agreement moved
to the level that decides something: the verdict and the four criteria,
which every node derives in code from its own reading.

This is only safe because of the gate above: `_parse_payload` re-derives the
verdict and the criteria from the payload's own findings and refuses a
payload whose outcome does not follow from them. A leader therefore cannot
report `COVERAGE_SUPPORTED` while its own rows say a condition was not met -
the payload is rejected before any comparison happens. Both halves are
tested: `test_gate_units.py` proves the outcome must follow from the
findings, and `test_validators.py` proves a forged outcome is refused while
a differently-labelled route to the same outcome is accepted.

Never equivalent, whatever the labels say:

```text
COVERAGE_SUPPORTED vs anything else
any criterion true vs false
a document examined vs unavailable, or unavailable for a different reason
a required kind present vs missing
a panel that assessed vs one that did not
a measurement found vs not found, or a different number
an accusation made vs not made
a directed-text count of zero vs any count above zero
```

## Forged-leader defence

The validator is a custom `gl.vm.run_nondet_unsafe` validator precisely
because the leader's result is treated as adversarial. These are the attacks
it refuses, each covered by a test in `tests/direct/test_validators.py` that
runs the contract's own validator closure through
`direct_vm.run_validator`:

| A leader that... | is rejected because |
|---|---|
| claims a claim is covered when this node did not reach that verdict | the verdict is compared |
| claims a criterion this node did not find | all four criteria are compared |
| claims a condition was met, with a quote that is not in the document | the quote is checked against this node's own bytes |
| offers one document's words as proof of what another says | each quote is checked against the document it names |
| reports an outcome its own findings do not produce | the gate re-derives both before any comparison |
| smuggles `1` where a boolean belongs, or a float where an integer does | types are checked exactly |
| smuggles an unknown finding, status, reason or panel state | every enum must be a known value |
| re-points the payload at another submission, claim, round, version or document set | all of those bindings are checked against state |
| claims documents were read when this node cannot fetch them | document statuses and reasons are compared |
| claims a document is unavailable when this node reads it fine | the same comparison, in the other direction |
| reports a different measurement, or invents one | `value_found` and `value` are compared, and the quote must be grounded |
| accuses the claimant where the policy asked no question | an unsolicited answer makes the whole response unusable |
| accuses the claimant without quoting the document | an accusation without a quote is refused by the gate |
| hides that the evidence addresses its reader | the marker count is compared |
| adds a row, drops a row, or reorders the conditions | the row set must match the policy's own |
| returns prose, nothing, or a truncated object | the payload must parse into the exact structure |

True-controls are tested alongside: an honest leader is agreed with,
reworded reasoning is agreed with, a different but grounded quote is agreed
with, and a differently-labelled route to the same outcome is agreed with.
Without those, a validator that always said no would look perfect.

## Leader failures

| Leader error | Validator agrees when |
|---|---|
| `[PANEL] ...` | never. The next round can read the documents again; a panel failure is not a fact about the world. |
| `[TRANSIENT] ...` | this node's own run also failed transiently. |
| `[EXPECTED] ...` and anything else prefixed | this node's own run failed with the identical message. |
| unprefixed | never. |

If the validator's own reproduction succeeds, it does not agree that the
work was impossible.

## Failure semantics

| Situation | Verdict | Terminal? |
|---|---|---|
| the policy document, or a document of a required kind, could not be examined | `EVIDENCE_UNAVAILABLE` | no, retryable |
| the panel answered unusably | `INCONCLUSIVE` | no, retryable |
| a condition was read but cannot be settled | `INCONCLUSIVE` | no, retryable |
| two documents contradict each other on a fact that matters | `INCONCLUSIVE` | no, retryable |
| the evidence is not sufficient to answer the question asked | `INCONCLUSIVE` | no, retryable |
| a declared trigger's measurement could not be read | `INCONCLUSIVE` | no, retryable |
| the policy asked a fraud question and the answer did not settle it | `INCONCLUSIVE` | no, retryable |
| the evidence addresses its reader and every condition otherwise stood | `INCONCLUSIVE` | no, retryable |
| the retry limit is reached while still unsettled | the same verdict, status `RESOLVED` | yes, and never consumable |
| validators cannot agree | the transaction commits no verdict | n/a |

Nothing uncertain becomes positive. `is_coverage_supported` is false for
every retryable state, for a cancelled claim, for a revoked policy version
and for a stale verdict.

A protocol-level `UNDETERMINED` transaction is not the contract's
`INCONCLUSIVE`. The first means the network could not decide the
transaction and no state changed - which is what the first live run
produced. The second is a recorded reading that could not settle, and it is
stored with the round that produced it.

## Why consensus is load-bearing

Remove consensus and the contract loses the only inputs it cannot compute:
whether each coverage condition is met on this evidence, whether an
exclusion is evidenced, and whether the documents contradict each other.
Everything else here is deterministic - and worth nothing without those,
because the whole question is whether what the documents show satisfies what
the policy requires.

Keep a single reader instead of consensus and something else breaks: the
ability to tell a true reading from a purchased one. The validator exists so
that the party deciding the claim cannot be the party whose reading of it
counts.
