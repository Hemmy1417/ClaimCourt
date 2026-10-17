# Why this primitive, and why it is this shape

## The primitive

ClaimCourt answers one question, repeatedly, for anyone who needs it
answered by somebody other than the party being asked about:

> A decision notice refused a claim and gave reasons, each citing a clause
> of a published policy. Is each reason actually supported by the clause it
> cites, as that clause is written?

The subject under judgment is **a decision and its stated rationale**. Not
whether a loss happened. Not whether the claimant's proof is good enough.
Not whether the claim should be paid. Whether the refusal, as written,
stands up against the rule it invokes.

## The trust question

Refusals are written by the party that benefits from them. The reasons are
in prose, the rule they cite is in prose, and checking one against the other
means reading both. That reading is normally done by the same organisation
that wrote the refusal, or by a reviewer the organisation chose and pays, or
- increasingly - by a model behind that organisation's backend. In all three
cases the author of the decision controls the review of the decision.

A claimant, a platform acting for one, an ombudsman service, or a
downstream contract cannot check the review themselves unless two things
are true: the documents are fixed, and the reading is reproducible by
someone with no stake. ClaimCourt makes the first true by binding both
documents to the sha256 of their exact bytes, and the second true by having
every validator fetch, hash and read them independently and agree
ground-by-ground.

## Delete GenLayer: what breaks?

Without GenLayer, the reading is done by one party's software. Whoever runs
it chooses the model, chooses the prompt, chooses which bytes to read, and
authors the conclusion. Nobody else can tell the difference between

- "the clause does not reach this ground", and
- "the operator's reviewer was configured to say so",

because the only artefact is an answer. There is no way for a counterparty
to establish that the quote the reviewer relied on is in the document, or
that the document read was the document issued.

What GenLayer adds is not decentralisation in the abstract. It is this:
**independent validators re-fetch the same hash-bound bytes, re-read them,
and the round only commits if they agree on the fields that decide the
outcome.** A leader that returns a well-formed, confident, substantively
false result is rejected by every honest validator, because each one checks
the leader's claims against bytes it verified itself, including whether
every quote exists at all.

Deterministic contract logic then decides what that agreement is allowed to
do: it owns authorisation, versioning, hashing, the literal triage bits,
quote grounding, verdict precedence, retry limits, counters, freshness and
every reliance gate. The model is never asked whether a claim should be
paid, or even what the verdict is. It is asked which grounds the clause
reaches.

## Why not a deterministic contract alone

A deterministic contract can check that a document hashes to a committed
digest, that a clause label literally occurs in the policy bytes, and that
a notice is no larger than a cap. It cannot decide whether clause 3.3,
which says a late notification "does not by itself end the cover", reaches
a ground that says the cover ended because notification was late. That is
reading, and it is the whole question.

The contract therefore uses the cheap deterministic checks as **triage**
only. The literal presence of a clause label is recorded as a fact and
agreed on by validators, but it never settles whether the clause was
located: a label can be present and the provision still be absent, and a
provision can be unmistakably there under different formatting.

## Why not a single LLM call

Two reasons, and the second is the one that matters.

1. A single call is a single authority. The operator who makes it can pick
   the model and the prompt, and nothing in the result is checkable.
2. A notice is written by the party under review. It can address the
   reviewer directly - the demonstration fixtures include one that tells
   its reader to report every ground as supported. A single-call design
   has nothing outside the model to catch that. Here, code counts the
   markers, validators must agree on the count, and a notice that addresses
   its reader cannot produce an upholding at all.

## Three consumers that do not change the contract

1. **Claims and dispute platforms** deciding whether a refusal should go to
   human review or to a regulator. They read `review_outcome` and escalate
   when `denial_unsupported` is true, or when the verdict is
   `DENIAL_OVERBROAD`.
2. **Settlement and escrow contracts** holding a disputed amount. They gate
   release on `is_denial_supported(review_id, as_of)` - a single boolean
   that is false for everything uncertain, stale, withdrawn or revoked.
3. **Conduct and quality monitors** reading `clause_record(clause_set_id,
   version, clause_ref)`: which clauses produce refusals that keep failing
   review. That is a drafting and practice signal nobody can see from
   individual cases, and it accumulates in the contract without any
   consumer having to index anything.

None of them needs web access, a prompt, an equivalence principle, or any
understanding of how consensus works.

## The collision audit

The audit was run across the repository owner's whole public portfolio
(every repository, not only the ones whose names suggest GenLayer) and
across the current public GenLayer material on when the protocol is
load-bearing, its documented use cases and its published examples.

The nearest patterns found, and why this is not one of them:

| Nearest pattern | What it judges | Why ClaimCourt is not it |
|---|---|---|
| Claim-evidence verification | Whether a claimant's submitted evidence satisfies a policy's criteria | Judges the claimant. ClaimCourt judges the decider: the claimant's evidence is not read, and a refusal can fail review while the claim itself remains unproven. |
| Parametric trigger determination | Whether a measured threshold was crossed in an insured window | Judges the world against a number. ClaimCourt judges prose against prose, and has no measurement in it. |
| Dispute adjudication between two parties | Which side public evidence supports | Produces a winner. ClaimCourt produces no winner: an unsupported refusal is not a payable claim, and the contract says so explicitly. |
| Specification or policy conformance | Whether an artefact meets a frozen specification | Judges an artefact against a rule. ClaimCourt judges *an assertion about a rule* - whether the rule, as written, says what somebody claimed it says. |
| Document authenticity and provenance | Whether bytes are what they claim to be | A precondition here, not the question. ClaimCourt hashes both documents and then reads them. |

The distinct axis is **review of an authority's stated rationale against the
rule it invokes, with both the rule and the rationale hash-bound, producing
a per-clause record of how refusals under that clause have held up.** No
pattern found occupies it, and the per-clause accumulating record has no
counterpart in any of the above.

The question also generalises past insurance without a line of change to
the contract, which is why its vocabulary is `clause set`, `decision
notice` and `grounds` rather than insurer wording: a refused benefit, a
denied permit, a rejected grant and a removed listing all have the same
shape - a decision, reasons, and a published rule the reasons cite.

## Candidates considered and rejected

Ten candidates were taken seriously. The scoring was: does GenLayer have to
decide it; is the evidence independently checkable by a validator; is the
output a small typed value rather than an essay; does state accumulate; can
three unrelated consumers use it unchanged; can a well-formed wrong leader
result be rejected; is it live-testable on a hosted network.

| Candidate | Rejected because |
|---|---|
| Review of a stated denial against the clause it cites | **Selected.** |
| Refusal-rate monitor across insurers | The evidence is private claim files; a validator cannot check anything. Open-ended aggregation, no decision. |
| Settlement-offer fairness scorer | "Fair" has no bounded standard in the inputs; the contract would be inventing the rule it applies. |
| Policy-wording readability grader | Open-ended content generation. No shared state transition, and nothing downstream gates on it. |
| Claim-document authenticity checker | The decisive evidence is usually not public, and the parts that are reduce to hashing, which needs no consensus. |
| Medical-necessity reviewer | Load-bearing evidence is private health data; it must never be on chain, and a validator cannot read it. Correctly out of scope. |
| Regulatory-deadline watchdog | Deterministic date arithmetic over public filings. A model adds nothing. |
| Ombudsman precedent matcher | Produces a similarity ranking, not a decision; similarity distance is not a holding, and the heuristic cannot be allowed to settle. |
| Complaint-category classifier | A classifier, not an adjudication. Nothing fails closed, nothing is gated. |
| Reinsurance treaty interpretation | Same shape as the selected candidate but with private contracts as evidence, so validators cannot reproduce the reading. |

## The hardest technical part

Quote grounding across independently fetched bytes. Every positive finding
the panel returns must carry a span of the document, and each validator
re-checks that span against its *own* verified copy, normalised for
whitespace and case but nothing else. Getting that right means the panel
cannot introduce language, and getting it wrong in either direction is
fatal: too strict and honest validators disagree over a line break, too
loose and an invented quote passes. The mutation sweep in `scripts/mutate.py`
breaks this rule, and three others around it, to prove the tests notice.

## Why this belongs in standalone Intelligent Contracts

One contract, one file, no frontend, no backend, no indexer, no token. A
small typed interface - one boolean for the common gate, one dict for the
full picture, one per-clause record - and a consensus round whose agreement
is confined by deterministic code on both sides. Nothing in it is a demo of
an application; all of it is a judgment other contracts can reuse without
reimplementing a trust boundary.
