# Why this primitive, and why it is this shape

## The primitive

ClaimCourt answers one bounded question, repeatedly, for anyone who needs it
answered by somebody other than the party deciding:

> Given a declared policy, a submitted claim, and independently observable
> evidence, does the claim satisfy the predefined conditions for coverage -
> or is there a specific policy-grounded reason it does not?

Not whether a claim *feels* genuine. Not a fraud score. Not a payout. One
typed adjudication result, bound to one version of one policy, on documents
every validator fetched and hashed itself.

## The trust question

Claims are decided by reconciling policy wording with incident reports,
invoices, assessors' figures, timestamps and published records. The hard
part is not collecting the documents. It is deciding whether what they show
satisfies the exact conditions the policy sets - while keeping apart what
the evidence supports, what a party merely asserts, what two documents
contradict, and what nobody can tell from the papers at all.

Today that reconciliation is done by the insurer's own staff, by an adjuster
it instructs, or by a model behind its own backend. Each is a single
authority, and the claimant cannot check any of them. Worse, the inputs are
mutable: a wording can be edited, a document can be swapped, and a decision
made last year cannot be re-examined against what the policy said at the
time.

ClaimCourt fixes both halves. The policy version, its coverage conditions,
its exclusions and the kinds of evidence a claim must carry are frozen and
hashed before any claim is submitted. Each evidence document is committed as
an `https` location plus the sha256 of its exact bytes. Then independent
validators fetch, hash and read the same bytes and must agree, condition by
condition, before anything is stored.

## Delete GenLayer: what breaks?

Without it, the reading is done by one party's software. Whoever runs it
chooses the model, the prompt and the bytes, and authors the conclusion.
Nobody else can distinguish

- "the evidence does not establish condition C4", from
- "the operator's assessor was configured to say so",

because the only artefact is an answer. There is no way for a claimant, a
regulator or a downstream contract to establish that the quote an adjudicator
relied on is in the document, or that the document read was the document
submitted, or that the wording applied was the wording in force.

What GenLayer adds is not decentralisation in the abstract. It is this:
**independent validators re-fetch the same hash-bound bytes, re-read them,
and the round commits only if they agree on the fields that decide the
outcome.** A leader that returns a well-formed, confident, substantively
false adjudication is rejected by every honest validator, because each one
checks the leader's findings against bytes it verified itself - including
whether every quote exists at all.

Deterministic contract logic then decides what that agreement is allowed to
do. It owns authorisation, versioning, hashing, the claim deadline, whether
the required kinds of evidence were supplied, quote grounding, the parametric
comparison, verdict precedence, retry limits, counters, freshness and every
reliance gate. The model is never asked whether to pay, nor what the verdict
is. It is asked which conditions the evidence meets.

## Why not a deterministic contract alone

Deterministic code can check that a document hashes to a committed digest,
that a claim arrived before the deadline, that every required kind of
evidence is present, and that a measured number crosses a threshold. It
cannot decide whether an assessor's description of layered tide marks and
rotted battens is "gradual deterioration" rather than "a sudden event", or
whether a door found closed but unlocked is "forcible and violent entry".
That is reading, and it is the part the parties actually dispute.

So the contract uses cheap deterministic checks as admission and as
settlement, and consensus only for the reading in between.

## Why not a single model call

Two reasons, and the second is the one that matters.

1. A single call is a single authority. The operator who makes it picks the
   model and the prompt, and nothing in the result is checkable.
2. The documents are supplied by a party with an interest in the outcome.
   They can address the reader directly - one demonstration fixture tells
   whoever reads it to report every condition as met and approve the claim.
   A single-call design has nothing outside the model to catch that. Here,
   code counts the markers, validators must agree on the count, and evidence
   that instructs its reader cannot produce a coverage verdict at all.

## The parametric case

A parametric policy pays on a measurement, not on a narrative, and that
makes the split sharp: the policy declares the measure, the unit, the rule,
the threshold, the insured window and the source. The panel reads the
measurement out of the published record and quotes the line it came from.
**Code does the comparison.** The model is explicitly told not to decide
whether the value crosses the threshold, the number is type-checked as a
whole integer in range, and the quote must occur in the bytes each validator
verified. A parametric trigger therefore cannot be fired by persuasion.

## Three consumers that do not change the contract

1. **Claims administration systems** deciding what happens next: pay,
   request more evidence, or escalate to a human. They read
   `claim_outcome(submission_id, as_of)` and branch on `verdict` and
   `evidence_status`.
2. **Settlement and escrow contracts** holding a disputed amount. They gate
   release on `is_coverage_supported(submission_id, as_of)` - a single
   boolean that is false for everything uncertain, stale, withdrawn or
   revoked.
3. **Parametric and risk systems** consuming trigger determinations in their
   own separately controlled workflows: `get_verdict` carries the trigger
   state and the criteria, and nothing in this contract moves a unit of
   value.

None of them needs web access, a prompt, an equivalence principle, or any
understanding of how consensus works.

## The collision audit

The audit was run across the repository owner's whole public portfolio -
every repository, not only the ones whose names suggest GenLayer - and
across the current public GenLayer material on when the protocol is
load-bearing, its documented use cases and its published examples.

The nearest patterns found, and how this stands against them:

| Nearest pattern | What it judges | Relationship to ClaimCourt |
|---|---|---|
| Claim-evidence verification against a versioned policy | whether committed claim evidence satisfies policy criteria, with fraud indicators | **This is the same lane.** The owner has shipped a contract that answers essentially this question. ClaimCourt is the brief's primitive and overlaps it deliberately; what it adds is the bounded claim *challenge* with its own decision question, required evidence kinds and deadline, a parametric trigger compared in code, and `EXCLUSION_APPLIES` as a verdict distinct from "not established". |
| Parametric trigger determination | whether a measured threshold was crossed in an insured window | A proper subset here: ClaimCourt treats a trigger as one condition among the policy's own, so a parametric policy and a narrative policy use the same contract. |
| Dispute adjudication between two parties | which side public evidence supports | Produces a winner. ClaimCourt produces no winner: an unestablished claim is not a fraudulent one, and the contract says so explicitly. |
| Specification or acceptance conformance | whether an artefact meets a frozen specification | Same shape, different domain and different failure semantics: there is no `EVIDENCE_UNAVAILABLE` or `EXCLUSION_APPLIES` in an acceptance primitive. |

**This overlap is stated rather than hidden.** The brief fixes the concept -
"do not replace this concept" - and the concept is adjacent to work already
in the portfolio. The honest position is that ClaimCourt is the brief's
primitive, built to the brief's schema, verdicts and views, with the
parametric trigger and the bounded challenge as the parts that are genuinely
its own.

## Candidates considered and rejected

The brief fixes the concept, so this is not an idea search. These are the
variants of *this* concept that were considered and rejected while designing
it:

| Variant | Rejected because |
|---|---|
| Claim vs versioned policy, challenge-bounded, evidence hash-bound | **Selected.** It is the brief's primitive and every input is checkable by a validator. |
| Adjudicate from the claimant's narrative alone | Caller-authored evidence. Nothing a validator can verify; the contract would be scoring prose. |
| Score fraud risk on every claim | A generic fraud score is explicitly out of scope, and incomplete evidence would become suspicion. Fraud is only ever answered where the policy asks a bounded question and the words are in the document. |
| Pay out on a supported verdict | The brief draws the payout boundary, and rightly: a verdict is an adjudication result, not an authorisation to move money. |
| Let the model decide whether a parametric trigger fired | Hands a threshold comparison to a reader. The model reads the number; code compares it. |
| Store the claim file on chain | Identity, medical and financial records must not be published, and a validator cannot read what it cannot fetch. Only hashes, references and synthetic data. |
| One contract per insurance line | Five contracts that differ by vocabulary. The policy is data: property, motor, travel, commercial and parametric crop all fit the same conditions-and-exclusions model. |

## The hardest technical part

Quote grounding across independently fetched bytes, with a downgrade rule
that is correct in both directions. Every substantive finding - `MET` and
`NOT_MET` alike, every evidenced exclusion, every contradiction, every
measurement, every fraud indicator - must carry a span of the document it
rests on, and each validator re-checks that span against *its own* verified
copy. An ungrounded finding is downgraded to the uncertain form, never to
its opposite: an accusation that cannot be quoted becomes "unclear", not
"innocent", and a condition that cannot be quoted becomes "unclear", not
"not met". Getting that wrong in either direction is fatal - too strict and
honest validators split over a line break, too loose and an invented quote
decides a claim. The mutation sweep in `scripts/mutate.py` breaks this rule
and the rules around it to prove the tests notice.

## Why this belongs in standalone Intelligent Contracts

One contract, one file, no frontend, no backend, no indexer, no token, no
payable path. A small typed interface - one boolean for the common gate, one
dict for the full picture, one per-policy-version record - and a consensus
round whose agreement is confined by deterministic code on both sides.
Nothing in it is a demo of an application; all of it is a judgment other
contracts can reuse without reimplementing a trust boundary.
