# ClaimCourt

**A reusable GenLayer Intelligent Contract that decides, under validator
consensus, whether a refusal's stated reasons are supported by the policy
clauses they cite - and treats the refusal as the thing on trial.**

A decider publishes the wording its decisions are made under; the document
is frozen and bound to the sha256 of its exact bytes. Anyone - the person
refused, a platform acting for them, an ombudsman service - opens a review
of a refusal notice, bound to its own bytes, naming each clause the notice
cites and each ground the notice gave. One consensus round has every
validator fetch and hash both documents itself, locate each cited clause,
and judge whether the clause **as written** reaches the ground the notice
relied on. Code decides every hard fact and names the verdict; every
positive finding must quote the document, and each validator re-checks
every quote against the bytes it verified itself. The contract records a
typed verdict any downstream contract reads in one view, and keeps a
per-clause record of how refusals under that clause have held up.

## Canonical deployment

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| Contract | [`0x78188E7554564606401b7f3B368076D08e0ef63E`](https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E) |
| Deployment tx | [`0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c`](https://explorer-studio.genlayer.com/tx/0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c) |
| Lifecycle | **FINALIZED**, execution SUCCESS, 3 agree / 0 disagree / 2 idle of 5 validators |
| Deployment source commit | `0ddcd67`, `contracts/claimcourt.py` |
| Source parity | the deployed bytes decode to sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` - **byte-identical** to this checkout, re-checked by `python scripts/verify.py` |
| Live evidence | [docs/proofs/live.md](docs/proofs/live.md) - five reviews, twelve FINALIZED transactions, every verdict and gate re-read off the chain |

Five reviews ran on that deployment against real validators reading real
documents: a refusal upheld; a refusal whose cited clause says in terms that
it does not reach the ground given; a refusal citing a clause that is not in
the wording; a jewellery-only limit used to refuse a whole claim; and a
refusal whose notice instructs whoever reads it, which could not be upheld.
`DENIAL_OVERBROAD` is exercised in Direct Mode but has not been produced
live - see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).


## At a glance

| Question | Answer |
|---|---|
| What is ClaimCourt | A standalone Intelligent Contract primitive: a review layer for refusals that cite a published rule. No frontend, no backend, no payouts, no token. |
| What does it decide | For each ground a refusal gave: is the cited clause in this version of the wording at all, does the notice actually state that ground, does the clause as written reach it, and does the notice stretch it past the clause's own scope. Then one typed verdict for the review. |
| What it does **not** decide | Whether the loss happened, whether the claimant's evidence is good, whether anything should be paid. The claimant's evidence is not read. |
| Why GenLayer must decide it | Checking a prose reason against a prose rule is reading. The party that wrote the refusal normally controls that reading - its own staff, its own chosen reviewer, or a model behind its own backend. GenLayer has independent validators re-fetch the same hash-bound bytes and agree ground by ground, and a well-formed but substantively false leader result is rejected by every honest one. |
| What evidence it uses | Exactly two documents, each an `https` location plus the sha256 of its exact bytes: the wording, and the notice. Both are hashed before anything reads them. |
| How consensus works | `gl.vm.run_nondet_unsafe`, once per round, with a custom validator that reproduces the whole round from its own fetches and gates the leader's payload against its own verified bytes. Prose is never compared; every stored quote is grounded. |
| How another contract consumes it | `is_denial_supported(review_id, as_of)` is the fail-closed boolean; `review_outcome(review_id, as_of)` is the full picture; `clause_record(...)` is the accumulating signal. See [docs/INTEGRATION.md](docs/INTEGRATION.md). |
| What tests prove it works | 176 Direct Mode tests, 131 source invariants, GenVM lint and SDK validation, a 29-mutation sweep (24 killed, 5 equivalent with the argument written out), plus a live Studionet run and a committed integration suite. See [docs/TESTING.md](docs/TESTING.md). |

## The problem

Refusals are written by the party that benefits from them, and they cite
rules in prose. "Declined under clause 3.3, notification was late" is a
claim about what clause 3.3 says. Checking it means reading the clause and
reading the notice, and most of the time whoever wrote the notice also owns
the review of it.

The gap that matters is not document collection. It is that nobody outside
the decider can establish two things: that the quote the review relied on
is actually in the document, and that the document reviewed is the document
issued.

## Why GenLayer

| Without it | What goes wrong |
|---|---|
| the decider's own backend | the author of the decision authors the review of the decision |
| one off-chain LLM call | a single configurable authority; nothing in the answer is checkable by a counterparty |
| a deterministic parser | can hash a document and find a clause label, but cannot decide whether a clause that says a late notification "does not by itself end the cover" reaches a ground that says the cover ended because notification was late |
| a price or data oracle | the wrong data type entirely; there is no number in this question |

### Delete GenLayer: what breaks?

Two inputs disappear, and they are the only two the contract cannot
compute: whether the cited clause is in the bound document at all, and
whether that clause as written reaches the stated ground. Everything else
here is deterministic - and worthless without those two, because the whole
question is prose against prose.

Keep a single reader instead of consensus and something else breaks: the
ability to tell a true reading from a purchased one. A notice can even
address its reader directly - one of the demonstration fixtures tells
whoever reads it to report every ground as supported. With one reader there
is nothing outside the model to catch that. Here code counts the markers,
validators must agree on the count, and such a notice cannot be upheld at
all.

## Why this is not a rejected pattern

- **Not a thin LLM wrapper.** The model answers four bounded questions per
  ground and never names a verdict, a status or a consequence. Precedence,
  grounding, admission, versioning, retries, counters and every reliance
  gate are deterministic.
- **Not a format-only validator.** The validator re-fetches, re-hashes and
  re-reads, then compares substantive fields and re-checks every quote
  against its own bytes. It rejects a perfectly well-formed, perfectly
  typed, substantively false leader result - 56 tests in
  `tests/direct/test_validators.py` do exactly that, with true-controls so
  a blind "no" would fail.
- **Not caller-authored evidence.** Neither party's assertions decide
  anything. Both documents are bound by hash before the reading, and a
  ground the notice does not state produces `GROUNDS_MISSTATED` - the
  opener's error, named as such.
- **Not toy storage.** Versioned, hashed clause sets; immutable review
  bindings; bounded grounds, rounds and histories; a per-clause tally that
  accumulates across reviews; explicit freshness and revocation.
- **Not an application.** One contract, one file, no UI, no server, no
  indexer, no token, no payable path.

## The verdicts

```
                    open_review / supersede_review
                                 |
                                 v
                                OPEN
                                 |
                         resolve_review
                                 |
      +--------------------------+---------------------------+
      |                          |                           |
  RESOLVED                   RETRYABLE                   WITHDRAWN
  DENIAL_SUPPORTED           INCONCLUSIVE                (opener, before
  DENIAL_UNSUPPORTED         RECORD_UNAVAILABLE           settlement)
  DENIAL_OVERBROAD                 |
  CLAUSE_MISCITED            retry_review, 3 rounds in total,
  GROUNDS_MISSTATED          then RESOLVED with the unsettled verdict
```

| Verdict | Meaning |
|---|---|
| `DENIAL_SUPPORTED` | every stated ground stands up against the clause it cites |
| `DENIAL_UNSUPPORTED` | at least one ground is not reached by the clause it cites |
| `DENIAL_OVERBROAD` | the clause reaches the ground, but the notice applies it wider than the clause's own stated scope - refusing a whole claim on a clause that limits one head of loss |
| `CLAUSE_MISCITED` | a cited clause is not in the bound version of the wording |
| `GROUNDS_MISSTATED` | the notice does not state a ground the review asserted |
| `INCONCLUSIVE` | read, not settled |
| `RECORD_UNAVAILABLE` | a bound document could not be examined |
| `WITHDRAWN` | taken back by the opener before settlement |

Three of these are ways of saying "no answer", and they are kept apart on
purpose. None of them is a finding against either side, and `is_consumable`
is false for all three.

Precedence is fixed and runs from "this review was framed wrongly" through
"the decider was wrong" to "the decision stands", so the most specific
defect always wins:

```
RECORD_UNAVAILABLE > INCONCLUSIVE > GROUNDS_MISSTATED > CLAUSE_MISCITED
                   > DENIAL_UNSUPPORTED > DENIAL_OVERBROAD > DENIAL_SUPPORTED
```

## Contract surface

**Writes** - `register_clause_set`, `publish_clause_version`,
`revoke_clause_version`, `open_review`, `resolve_review`, `retry_review`,
`withdraw_review`, `supersede_review`.

**Views** - `get_config`, `get_clause_set`, `clause_set_head`,
`definition_hash`, `get_review`, `get_grounds`, `get_receipt`,
`review_verdict`, `review_status`, `freshness`, `is_fresh`,
`is_consumable`, `is_denial_supported`, `is_denial_unsupported`,
`review_outcome`, `clause_record`, `clause_set_record`, `list_reviews`,
`notice_under_review`, `get_stats`.

Anyone may open a review and anyone may resolve one: the party whose
decision is under review does not get to decide whether it is reviewed.
Only the clause set owner may publish or revoke a version, and only the
opener may withdraw a review.

## Nondeterministic operations

| Call | Where | Why it is irreducibly nondeterministic |
|---|---|---|
| `gl.nondet.web.get(policy_url)` | `_fetch_doc` | the wording lives off chain |
| `gl.nondet.web.get(notice_url)` | `_fetch_doc` | so does the notice |
| `gl.nondet.exec_prompt(..., response_format="json")` | `_node_round` | whether a clause as written reaches a stated ground is reading |

All three happen inside one round. There is no second round and no second
prompt.

## Deterministic responsibilities

Ownership and authorisation; identifiers and sequences; the sha256 of both
documents, checked before any byte is decoded; the URL admission rules;
every bound (grounds, rounds, versions, reviews per version, URL and text
lengths, quote length, document size, page size); the clause-label and
asserted-ground literal triage bits; the count of text addressed to the
reader; quote grounding against each node's own bytes; each ground's
outcome; verdict precedence; the directed-text ceiling; status
transitions and terminal replay; the notice registry; counters; freshness
arithmetic; and every reliance gate.

The model is never asked whether a claim should be paid, nor what the
verdict is.

## Equivalence

Must match: schema, review id, round, definition hash, both document
digests, both document statuses, the directed-text count, the panel state,
and per ground the clause reference, `clause_located`,
`ground_stated_in_notice`, `supported`, `scope_exceeded`, `outcome` and the
two literal triage bits.

May differ: one sentence of reasoning per ground, and which grounded span
was quoted. A quote may differ; every quote must be **grounded** in the
bytes that node verified. Requiring identical spans would make honest
validators disagree over nothing. Requiring none would let a leader invent
language.

Full detail, including the forged-leader table: [docs/CONSENSUS.md](docs/CONSENSUS.md).

## Failure semantics

Every default is the cautious one. A document that cannot be fetched, is
the wrong bytes, is too large or is not readable text gives
`RECORD_UNAVAILABLE`. An unusable panel answer gives `INCONCLUSIVE`. An
ungrounded "located" is not located. An unknown enum value, a wrong type or
a missing field is a failure, not a default. A notice that addresses its
reader cannot be upheld. `is_consumable` is false for every retryable
state, for a withdrawn review, for a revoked clause version and for a stale
one.

A protocol-level `UNDETERMINED` transaction is not the contract's
`INCONCLUSIVE`: the first means no state changed, the second is a recorded
reading that could not settle.

## Reuse surface

```python
@gl.contract_interface
class IClaimCourt:
    class View:
        def is_denial_supported(self, review_id: str, as_of: str) -> bool: ...
        def review_outcome(self, review_id: str, as_of: str) -> dict: ...
    class Write:
        pass


if not IClaimCourt(COURT).view().is_denial_supported(review_id, as_of):
    raise gl.vm.UserError("EXPECTED: the refusal has not been upheld")
```

Three consumers that need no change to the contract: dispute platforms
deciding whether to escalate a refusal; settlement contracts holding a
disputed amount until a refusal fails review; conduct monitors reading
`clause_record` to see which clauses produce refusals that keep failing.
None needs web access, a prompt, an equivalence principle, or any knowledge
of consensus. See [docs/INTEGRATION.md](docs/INTEGRATION.md).

The contract's vocabulary is `clause set`, `decision notice` and `grounds`
rather than insurer wording, because a refused benefit, a denied permit, a
rejected grant and a removed listing all have the same shape: a decision,
reasons, and a published rule the reasons cite.

## Limitations

- Not legal advice, not a regulatory determination, not an ombudsman
  decision. A verdict obliges nobody to pay anything.
- `DENIAL_UNSUPPORTED` means the stated reason did not stand up on the two
  documents reviewed. It does not mean the claim is valid, or that a
  different reason would not stand.
- `DENIAL_SUPPORTED` means the stated reasons stood up as written. It does
  not mean the decision was fair, proportionate or lawful.
- The contract cannot tell whether the published wording is the wording a
  claimant actually bought, only that it is the wording the review was
  bound to.
- The URL rules are defence in depth, not SSRF prevention; a validator
  runtime's egress policy matters as much.
- Prompt-injection handling is layered - data framing, marker counting,
  quote grounding, a verdict ceiling - and layered is not immune.
- Honest validators may word reasoning differently; only the
  decision-critical fields are consensus-critical, by design.
- A genuinely close reading may land on `INCONCLUSIVE`. That is the
  intended behaviour, not a failure.
- Documents must be public: a validator has to be able to fetch them.
  Anything that cannot be published should not be reviewed here.
- This is a Studionet deployment for demonstration and reuse, not an
  audited production system.

## Verification

```bash
python scripts/preflight.py                      # 131/131
pytest tests/direct -q                           # 176 passed
genvm-lint lint  contracts/claimcourt.py         # lint passed
genvm-lint check contracts/claimcourt.py         # validation passed
python scripts/mutate.py                         # 24/29 killed, 5 equivalent
```

Live, against the deployment recorded above:

```bash
gltest tests/integration -v -s --network studionet
```

Everything each gate actually printed is in [docs/TESTING.md](docs/TESTING.md),
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and `docs/proofs/live.md`.

## Reviewer fast path

```bash
git clone https://github.com/Hemmy1417/ClaimCourt.git
cd ClaimCourt
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
python -m pip install -r requirements-test.txt
python scripts/preflight.py
pytest tests/direct -q
```

No network, no keys and no GenLayer account are needed for any of that. To
read what the live run did instead of running it, open
[docs/proofs/live.md](docs/proofs/live.md).

## Repository

```
contracts/claimcourt.py              the one deployable contract
tests/direct/                        176 tests, no network
tests/integration/                   hosted Studionet suite
fixtures/                            synthetic wording and notices
scripts/preflight.py                 source invariants, no dependencies
scripts/mutate.py                    mutation sweep
scripts/live.py                      live evidence driver
docs/CONSENSUS.md                    the round, equivalence, forged leaders
docs/SECURITY.md                     threat model and fail-closed policy
docs/INTEGRATION.md                  how another contract consumes it
docs/DEPLOYMENT.md                   canonical deployment evidence
docs/TESTING.md                      every gate and the mutation sweep
docs/proofs/live.md                  the live run, transaction by transaction
DECISION.md                          why this primitive, and the collision audit
SUBMISSION.md                        copy-ready submission notes
```

Everything in `fixtures/` is synthetic, labelled `TEST / DEMONSTRATION
ONLY` and `NOT FOR PRODUCTION`. No real policy, notice, insurer or person
appears anywhere in this repository.

MIT licensed.
