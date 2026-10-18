<p align="center">
  <img src="docs/assets/claimcourt-mark.svg" width="96" height="96" alt="ClaimCourt">
</p>

<h1 align="center">ClaimCourt</h1>

<p align="center">A claim, a policy, and the documents. Does the claim satisfy the conditions for coverage, or is there a policy-grounded reason it does not?<br>
A standalone GenLayer Intelligent Contract. No frontend, no token, no payouts.</p>

<p align="center">
  <a href="https://github.com/Hemmy1417/ClaimCourt/actions/workflows/gates.yml"><img src="https://github.com/Hemmy1417/ClaimCourt/actions/workflows/gates.yml/badge.svg" alt="gates"></a>
</p>

## Thesis

Deciding a claim means reconciling policy wording with incident reports,
invoices, assessors' figures and published records - and keeping apart what
the evidence supports, what a party asserts, what two documents contradict,
and what nobody can tell from the papers at all. Today that reconciliation
is done by the insurer's own staff, an adjuster it instructs, or a model
behind its own backend, and the claimant cannot check any of them.

ClaimCourt freezes the policy version, its coverage conditions, its
exclusions and the kinds of evidence a claim must carry, and hashes all of
it before any claim is submitted. Each evidence document is committed as an
`https` location plus the sha256 of its exact bytes. Independent validators
then fetch, hash and read the same bytes and must agree on what the claim
comes to. Deterministic code decides everything code can decide - including
the verdict, and including whether a parametric trigger fired.

## Canonical deployment

| | |
|---|---|
| Network | GenLayer Studionet, chain id 61999 |
| Contract | [`0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a`](https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a) |
| Explorer | `https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a` |
| Deployment tx | [`0x7672910d8d84f12df786b3e728a7027288a717d1828607225301087391e9bb93`](https://explorer-studio.genlayer.com/tx/0x7672910d8d84f12df786b3e728a7027288a717d1828607225301087391e9bb93) |
| Finality / status | FINALIZED, leader execution SUCCESS |
| Consensus result | 3 agree, 0 disagree, 2 idle of 5 validators |
| Source | [`contracts/claimcourt.py`](contracts/claimcourt.py), one file, deployed as it stands |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Deployment source commit | `4a6fcc9` |
| Current source parity | the deployed contract read back with `gen_getContractCode` decodes **byte-identical** to `contracts/claimcourt.py` (sha256 `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4`) |
| Live record | [`docs/proofs/live.md`](docs/proofs/live.md) - five claims under three policies, every verdict and every quoted finding re-read off the chain by `scripts/verify.py` |

## The question

> Given a declared policy, a submitted claim, and independently observable
> evidence, does the claim satisfy the predefined conditions for coverage -
> or is there a specific policy-grounded reason it does not?

Not whether a claim feels genuine. Not a fraud score. Not a payout.

## The problem

The hard part of a disputed claim is not collecting documents. It is
deciding whether what they show satisfies the exact conditions the policy
sets, when the evidence may be incomplete, contradictory or hard to read -
and doing it in a way the party who loses can check.

Two things have to be true for that: the inputs must be fixed, and the
reading must be reproducible by someone with no stake. A wording that can
be edited after the fact, or a document that can be swapped, makes any
verdict unfalsifiable.

## Why GenLayer

| Without | What is left |
|---|---|
| the insurer's own backend | the party deciding the claim also owns the review of the decision |
| one off-chain model call | a single configurable authority; nothing in the answer is checkable by a claimant |
| a deterministic parser | it can hash a document, check a deadline and compare a number, but it cannot decide whether an assessor's layered tide marks are "gradual deterioration" or a door left unlocked is "forcible entry" |
| a price or data oracle | the wrong data type: most of this question is prose, and the part that is a number is already handled in code |

| Who | Decides |
|---|---|
| The contract, deterministically | who may publish or revoke a policy version, which version a claim is bound to, whether it arrived before the deadline, whether the required kinds of evidence were supplied, the sha256 of every document, whether a quote occurs in the bytes a node verified, whether a measurement crossed its threshold, the verdict, the retry limit, the counters and every reliance gate |
| GenLayer consensus | whether each coverage condition is met on this evidence, whether an exclusion is evidenced, whether the documents contradict each other - agreed by a panel that each read the same hash-bound bytes |
| The model | reading the documents and answering those bounded questions, quoting the words it answers from |

## Delete GenLayer: what breaks?

Three inputs disappear, and they are the only three the contract cannot
compute: whether each condition is met, whether an exclusion is evidenced,
and whether the documents contradict each other. Everything else here is
deterministic - and worthless without those, because the whole question is
whether what the documents show satisfies what the policy requires.

Keep a single reader instead of consensus and something else breaks: the
ability to tell a true reading from a purchased one. A claimant's own
documents can address whoever reads them - one demonstration fixture tells
its reader to report every condition as met and approve the claim. With one
reader there is nothing outside the model to catch that. Here code counts
the markers, validators agree on the count, and such a claim cannot become
covered. That ran on the live network: two conditions read as met, five
markers counted, verdict `INCONCLUSIVE`, every gate false.

## Why this is not a rejected pattern

- **Not a thin model wrapper.** The model answers bounded questions about
  documents and never names a verdict, a status, a consequence, or whether
  a threshold was crossed.
- **Not a format-only validator.** Each validator re-fetches, re-hashes and
  re-reads, then checks the leader's payload against its own bytes and
  compares the outcome. It rejects a well-formed, perfectly typed,
  substantively false adjudication.
- **Not caller-authored evidence.** Every document is bound by sha256
  before anything reads it, and a finding that cannot be quoted does not
  stand.
- **Not a fraud score.** `FRAUD_INDICATORS_FOUND` exists only where the
  policy asks a bounded question, needs a grounded quote, and is never
  reachable from missing evidence.
- **Not toy storage.** Versioned, hashed policies; immutable claim
  bindings; bounded conditions, exclusions, documents, rounds and
  histories; a per-version record that accumulates; explicit freshness and
  revocation.
- **Not an application.** One contract, one file, no UI, no server, no
  indexer, no token, no payable path.

## The verdicts

| Verdict | Meaning |
|---|---|
| `COVERAGE_SUPPORTED` | every coverage condition is met on this evidence, no exclusion is evidenced, and any declared trigger fired |
| `COVERAGE_NOT_ESTABLISHED` | a condition is positively not met, or a declared trigger did not fire |
| `EXCLUSION_APPLIES` | an exclusion is evidenced, with the words it rests on stored beside it |
| `FRAUD_INDICATORS_FOUND` | the policy asked a bounded fraud question and the documents answer it, with a quote |
| `INCONCLUSIVE` | read, not settled |
| `EVIDENCE_UNAVAILABLE` | the policy document or a required kind could not be examined |
| `CANCELLED` | the claimant withdrew the claim before it settled |

Precedence is fixed, and nothing uncertain can become a positive result:

```text
EVIDENCE_UNAVAILABLE > INCONCLUSIVE > FRAUD_INDICATORS_FOUND
                     > EXCLUSION_APPLIES > COVERAGE_NOT_ESTABLISHED
                     > COVERAGE_SUPPORTED
```

A claim not established is **not** a fraudulent claim, and the contract
keeps the two apart on purpose. Unavailable evidence is never a finding
against anyone, and a claim that cannot be settled stays unsettled and
retryable rather than being forced into an answer.

## Lifecycle and who moves it

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

| Step | Who | When |
|---|---|---|
| `register_policy` | anyone; the caller becomes owner | publishes version 1 with its conditions, exclusions, optional fraud question and optional parametric trigger |
| `publish_policy_version` | the owner | a new version with its own policy hash; submitted claims keep theirs |
| `revoke_policy_version` | the owner | that version's claims stop being consumable, keeping their verdicts |
| `open_claim_challenge` | the owner | the bounded question, the kinds of evidence a claim must carry, the deadline |
| `submit_claim` | **anyone** | binds the version, its hash and every document by sha256 |
| `resolve_submission` | anyone | one consensus round |
| `retry_submission` | anyone | only a claim adjudicated but not settled, within the round limit |
| `cancel_submission` | the claimant | only before settlement |

## Contract surface

**Writes** - `register_policy`, `publish_policy_version`,
`revoke_policy_version`, `open_claim_challenge`, `cancel_claim_challenge`,
`submit_claim`, `resolve_submission`, `retry_submission`,
`cancel_submission`.

**Views** - `get_config`, `get_policy`, `get_claim`, `get_claim_status`,
`get_policy_hash`, `get_policy_version`, `get_submission`, `get_verdict`,
`get_evidence_status`, `get_findings`, `get_receipt`,
`is_coverage_supported`, `freshness`, `is_fresh`, `is_consumable`,
`claim_outcome`, `policy_record`, `list_submissions`, `evidence_first_seen`,
`get_stats`.

`get_receipt(submission_id, round)` returns the ratified payload of that
round: the document rows, the marker count, the panel state, every grounded
finding, the measurement, the criteria and the verdict. That is the audit
trail - what the validators agreed on, not a summary of it.

## Nondeterministic operations

| Call | Where | Why it is irreducibly nondeterministic |
|---|---|---|
| `gl.nondet.web.get(policy_url)` | `_fetch_doc` | the wording lives off chain |
| `gl.nondet.web.get(evidence_url)` | `_fetch_doc`, per document | so does the claim file |
| `gl.nondet.exec_prompt(..., response_format="json")` | `_node_round` | whether the evidence meets a condition, whether an exclusion is evidenced, and whether documents contradict each other, is reading |

All of it happens inside one round. Every document is hashed before anything
reads it: bytes whose sha256 does not match the commitment are never
decoded, never excerpted and never shown to a model.

## Deterministic responsibilities

Ownership and authorisation; identifiers and sequences; the policy hash over
the whole definition; every document digest; the URL admission rules; the
claim deadline; whether the required kinds of evidence were supplied, and
whether they turned out readable; every bound; the count of text addressed
to the reader; quote grounding against each node's own bytes; the parametric
comparison; the four criteria; verdict precedence; the directed-text
ceiling; status transitions and terminal replay; the counters; freshness
arithmetic; and every reliance gate.

## Equivalence

Must match: the schema, the identifiers and bindings, both document
digests, each document's status and reason, the missing-kinds list, the
directed-text count, the panel state, the trigger state, the measurement,
and **the verdict**.

May differ: the label on an individual condition or exclusion, the four
criteria where the verdict does not pin them, which grounded span was
quoted, and the sentence of reasoning.

In one line: **the facts must match, the outcome must match, and the
reasoning may differ.** That is safe only because the gate re-derives the
verdict and the criteria from the payload's own findings and refuses one
that does not follow - so a leader cannot report an outcome its own rows
contradict. Two live rounds taught this the hard way, and
[docs/CONSENSUS.md](docs/CONSENSUS.md) records both.

## Safety and failure semantics

Every default is the cautious one. A document that cannot be fetched, is the
wrong bytes, is too large or is not readable text gives
`EVIDENCE_UNAVAILABLE`. An unusable panel answer gives `INCONCLUSIVE`. An
ungrounded finding is downgraded to `UNCLEAR` - never to its opposite, so an
accusation that cannot be quoted becomes uncertainty rather than innocence,
and a condition that cannot be quoted becomes uncertainty rather than
refusal. An unknown enum value, a wrong type or a missing field is a
failure, not a default. Evidence that addresses its reader cannot win
coverage.

A protocol-level `UNDETERMINED` transaction is not the contract's
`INCONCLUSIVE`: the first means no state changed, the second is a recorded
reading that could not settle.

## Financial safety, privacy, and no false guarantees

Nothing here moves money. There is no payable method, no token, no bond and
no balance: a verdict is a machine-readable adjudication result, and any
payout system must separately enforce its own authorisation, limits,
finality and insurer rules.

Nothing identifying belongs on chain. The contract stores document locations
and digests, a short claimant reference, a bounded incident summary, a date,
a location reference, a loss category, an amount **band**, the grounded
quotes, the findings and the counters. Identity documents, medical records,
bank statements and adjuster files must not be put here, and every document
a claim commits becomes public by construction because a validator has to
fetch it.

`COVERAGE_SUPPORTED` does not guarantee payment.
`COVERAGE_NOT_ESTABLISHED` is not a finding that a claim is false.
`FRAUD_INDICATORS_FOUND` is indicators in these documents under this
policy's own question - not a determination of fraud. One adjudication
proves nothing about any other claim.

## Reuse surface

```python
@gl.contract_interface
class IClaimCourt:
    class View:
        def is_coverage_supported(self, submission_id: str,
                                  as_of: str) -> bool: ...
        def claim_outcome(self, submission_id: str, as_of: str) -> dict: ...
    class Write:
        pass


if not IClaimCourt(COURT).view().is_coverage_supported(submission_id, as_of):
    raise gl.vm.UserError("EXPECTED: coverage is not supported")
```

Three consumers that need no change to the contract: claims administration
systems deciding whether to pay, request more evidence or escalate;
settlement contracts holding a disputed amount until coverage is
adjudicated; and parametric systems consuming trigger determinations in
their own workflows. None needs web access, a prompt, an equivalence
principle, or any knowledge of consensus.
[docs/INTEGRATION.md](docs/INTEGRATION.md) has the details, including how to
pin the policy hash a verdict was produced under.

## Limitations

- Not legal advice, not a regulatory determination, not a replacement for a
  licensed adjuster or an insurer's own claims process.
- A verdict speaks only about the documents reviewed under one policy
  version. It obliges nobody.
- The contract cannot tell whether a published wording is the policy a
  claimant actually holds, only that it is the one the claim was bound to.
- The URL rules are defence in depth, not SSRF prevention; a validator
  runtime's egress policy matters as much.
- Prompt-injection handling is layered - data framing, marker counting,
  quote grounding, a verdict ceiling - and layered is not immune.
- Honest validators may label an individual condition differently; only the
  facts and the outcome are consensus-critical, by design.
- A genuinely close claim may land on `INCONCLUSIVE`, as one live scenario
  did. That is the intended behaviour, not a failure.
- Studionet deployment for demonstration and reuse, not an audited
  production system.

## Verification

| Gate | Command | Result |
|---|---|---|
| source invariants | `python scripts/preflight.py` | 167/167 |
| Direct Mode | `pytest tests/direct -q` | 229 passed, 0 failed, 0 skipped |
| GenVM AST lint | `genvm-lint lint contracts/claimcourt.py` | passed, 3 checks |
| GenVM SDK validation | `genvm-lint check contracts/claimcourt.py` | passed, 29 methods (20 view, 9 write) |
| mutation sweep | `python scripts/mutate.py` | see [docs/TESTING.md](docs/TESTING.md) |
| hosted integration | `CLAIMCOURT_FIXTURE_REF=4a6fcc9 gltest tests/integration -v -s --network studionet` | see [docs/TESTING.md](docs/TESTING.md) |
| live evidence, re-read | `python scripts/verify.py` | all checks passed; read-only, no keys |
| CI, every push | `.github/workflows/gates.yml` | the offline gates on ubuntu |

## Reviewer fast path

```bash
git clone https://github.com/Hemmy1417/ClaimCourt.git
cd ClaimCourt

# Windows, the environment these results come from
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-test.txt
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/preflight.py
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest tests/direct -q

# POSIX
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-test.txt
python scripts/preflight.py
pytest tests/direct -q
```

No network, no keys and no GenLayer account are needed for any of that, once
the GenVM runner bundle is cached (both `gltest` and `genvm-linter` fetch it
into `~/.cache/` on first use). To check the live deployment instead of
re-running it, `python scripts/verify.py` reads every recorded transaction,
document, verdict and finding back off Studionet and rewrites
[`docs/proofs/live.md`](docs/proofs/live.md) from what it finds.

## Repository

```text
contracts/claimcourt.py              the one deployable contract
tests/direct/                        229 tests, no network
tests/integration/                   hosted Studionet suite
fixtures/                            synthetic policies, claims and records
scripts/preflight.py                 source invariants, no dependencies
scripts/mutate.py                    mutation sweep
scripts/live.py                      live evidence driver
scripts/verify.py                    read-only re-check of the live run
scripts/fetch_genvm_bundle.py        seeds the GenVM runner bundle for CI
docs/CONSENSUS.md                    the round, equivalence, forged leaders
docs/SECURITY.md                     threat model and fail-closed policy
docs/INTEGRATION.md                  how another contract consumes it
docs/DEPLOYMENT.md                   canonical deployment evidence
docs/TESTING.md                      every gate and the mutation sweep
docs/proofs/live.md                  the live run, claim by claim
docs/proofs/live.json                the ledger scripts/verify.py reads back
DECISION.md                          why this primitive, and the collision audit
SUBMISSION.md                        copy-ready submission notes
```

Everything in `fixtures/` is synthetic and labelled `TEST / DEMONSTRATION
ONLY` and `NOT FOR PRODUCTION`. No real policy, claim, insurer or person
appears anywhere in this repository.

## Licence

MIT. See [LICENSE](LICENSE).
