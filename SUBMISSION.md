# Submission notes

Copy-ready. Every number here is one a command printed; nothing is
estimated.

## Identity

| Field | Value |
|---|---|
| Category | Standalone GenLayer Intelligent Contract |
| Title | ClaimCourt — adversarial insurance claim adjudication |
| Repository | https://github.com/Hemmy1417/ClaimCourt |
| Licence | MIT |
| Network | GenLayer Studionet, chain 61999 |

**One-line thesis.** ClaimCourt is a reusable GenLayer Intelligent Contract
that decides, under validator consensus, whether a submitted claim satisfies
the conditions for coverage declared by a specific version of a policy, on
evidence every validator fetches and hashes itself.

## Canonical deployment

| Field | Value |
|---|---|
| Contract | `0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a` |
| Explorer (portal evidence URL) | https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a |
| Deployment tx | `0x7672910d8d84f12df786b3e728a7027288a717d1828607225301087391e9bb93` |
| Lifecycle | FINALIZED, execution SUCCESS, 3 agree / 0 disagree / 2 idle of 5 |
| Deployment source | commit `4a6fcc9`, `contracts/claimcourt.py` |
| Source parity | deployed bytes byte-identical to the committed source (sha256 `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4`) |

## Why GenLayer is required

Deciding a claim means reading policy wording against incident reports,
invoices, assessors' figures and published records. Remove GenLayer and the
contract loses the only three inputs it cannot compute: whether each
coverage condition is met on this evidence, whether an exclusion is
evidenced, and whether the documents contradict each other. Keep a single
reader instead of consensus and it loses the ability to tell a true reading
from a purchased one — including against a claimant's own document that
instructs whoever reads it, which one demonstration fixture does on purpose.

## Consensus mechanism

One `gl.vm.run_nondet_unsafe` round with a custom validator. Every node
fetches and hashes the policy document and every evidence document itself,
counts text addressed to the reader in code, works out in code which
required kinds are actually readable, convenes one panel call, reads the
answer strictly, holds every finding to a quote from the bytes it verified,
compares any parametric measurement with the threshold in code, and derives
the four criteria and the verdict in code. Each validator reproduces all of
that independently and gates the leader's payload against its own bytes
before comparing.

Validators must agree on the facts and the verdict: the identifiers and
bindings, both document digests, each document's status and reason, the
missing-kinds list, the directed-text count, the panel state, the
measurement, the trigger state, the four criteria, and the verdict itself.
They may differ on the label of an individual condition, on the fraud
finding where it does not change the verdict, on which grounded span was
quoted, and on the reasoning. That is safe because the gate re-derives the
outcome from the payload's own findings and refuses one that does not
follow.

## Deterministic responsibilities

Authorisation, versioning, the policy hash over the whole definition, every
document digest, URL admission, the claim deadline, the required evidence
kinds, every bound, the directed-text count, quote grounding, the parametric
comparison, the four criteria, verdict precedence, status transitions and
terminal replay, the counters, freshness and every reliance gate. The model
is never asked what the verdict is, nor whether a threshold was crossed.

## Failure policy

Fail closed throughout. An unfetchable, substituted, oversized or unreadable
document gives `EVIDENCE_UNAVAILABLE`; an unusable panel answer or an
unsettled condition gives `INCONCLUSIVE`; an ungrounded finding is
downgraded to uncertainty, never to its opposite; an unknown value or wrong
type is a failure rather than a default; evidence that addresses its reader
cannot win coverage. Retries are capped at three rounds, after which the
claim resolves unsettled and is never consumable. A claim not established is
never called fraud.

## Reuse surface

`is_coverage_supported(submission_id, as_of)` is the fail-closed boolean,
`claim_outcome(...)` the full picture, `get_verdict(...)` the structured
result with the four criteria, and `policy_record(policy_id, version)` the
accumulating record. Three consumers that need no change to the contract:
claims administration systems deciding whether to pay, request more evidence
or escalate; settlement contracts holding a disputed amount; and parametric
systems consuming trigger determinations. Nothing in the contract moves
money.

## Test results

| Gate | Result |
|---|---|
| source invariants (`scripts/preflight.py`) | 167/167 |
| Direct Mode (`pytest tests/direct -q`) | 233 passed, 0 failed, 0 skipped |
| pickling checks | on, passing |
| GenVM AST lint | passed, 3 checks |
| GenVM SDK validation | passed, 29 methods (20 view, 9 write) |
| mutation sweep (`scripts/mutate.py`) | <!-- SWEEP --> |
| hosted integration | 5 passed in 17 min 44 s on hosted Studionet |
| CI (`.github/workflows/gates.yml`) | the offline gates on ubuntu, green |

## Live evidence

Five synthetic claims under three policies, adjudicated by real validators
on the canonical deployment, then re-read off the network by
`python scripts/verify.py` (read-only, no keys):

| Scenario | Stored verdict |
|---|---|
| a claim whose conditions the evidence meets | `COVERAGE_SUPPORTED` |
| an exclusion the assessor's own words evidence | `EXCLUSION_APPLIES` |
| a theft condition the evidence does not settle | `INCONCLUSIVE` |
| a parametric trigger, 182 mm read from the published record | `COVERAGE_SUPPORTED`, trigger `MET` |
| evidence that instructs whoever reads it | `INCONCLUSIVE`, retryable, not consumable |

Three earlier live runs are recorded in `docs/DEPLOYMENT.md` rather than
hidden: two taught that the equivalence rule was too strict and split the
round, and one showed that a covered event cannot be established by the
claimant's own account of it. Full detail, including the sentences each
finding rests on: `docs/proofs/live.md`.

## Limitations

Not legal advice, not a regulatory determination, not a replacement for a
licensed adjuster. `COVERAGE_SUPPORTED` does not guarantee payment and
nothing in the contract moves money. `COVERAGE_NOT_ESTABLISHED` is not a
finding that a claim is false, and `FRAUD_INDICATORS_FOUND` is indicators in
these documents under this policy's own question, not a determination of
fraud. The contract cannot tell whether a published wording is the policy a
claimant holds. URL rules are defence in depth, not SSRF prevention.
Prompt-injection handling is layered, not immune. A genuinely close claim
may land on `INCONCLUSIVE`, as one live scenario did. Studionet deployment
for demonstration and reuse, not an audited production system. Every fixture
is synthetic and labelled.

## Reviewer fast path

```bash
git clone https://github.com/Hemmy1417/ClaimCourt.git
cd ClaimCourt
python -m venv .venv && .venv/Scripts/activate
python -m pip install -r requirements-test.txt
python scripts/preflight.py
pytest tests/direct -q
```

No network, no keys, no GenLayer account.

## Portal submission

This is an **Intelligent Contract** contribution, not a Project. There is no
app and no user journey: the deliverable is one deployed contract and the
evidence that it does what it says.

The portal validates one evidence URL specifically as
`genlayer-explorer-contract`. For a Studionet contract that is the Explorer
**address** page — not the repository, not a transaction, not the Studio
import link:

```text
https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a
```

Supporting evidence, where the form allows more than one link:

| What | URL |
|---|---|
| Repository | https://github.com/Hemmy1417/ClaimCourt |
| Deployment evidence | https://github.com/Hemmy1417/ClaimCourt/blob/main/docs/DEPLOYMENT.md |
| Live run, re-read off chain | https://github.com/Hemmy1417/ClaimCourt/blob/main/docs/proofs/live.md |

**Title**

```text
ClaimCourt - adversarial insurance claim adjudication
```

**One-liner**, if the form asks for one:

```text
Decides, under validator consensus, whether a claim satisfies the coverage conditions of a specific policy version, on evidence every validator fetches and hashes itself.
```

(170 characters, limit 180.)

**Verification outcome**, if the form asks for one:

```text
Open the contract on the explorer and read any claim: it stores the verdict, each condition and exclusion, and the words every finding rests on. The policy and each document are bound to the hash of their exact bytes, so anyone can fetch them, hash them, and confirm what was read. A read-only script in the repository re-queries every transaction and re-reads every stored result, and the deployed contract decodes back to the committed source.
```

(445 characters, limit 500.)

No addresses, hashes, identifiers or shell commands appear in any text
field; the contract address belongs only in the validated evidence URL.
**Contribution date** is the day you submit, not the build date. A 512px
raster of the mark is at `docs/assets/claimcourt-mark-512.png` if the form
asks for an image.

## Portal description (under 1000 characters)

ClaimCourt is a standalone GenLayer Intelligent Contract that adjudicates insurance claims. An insurer publishes a policy version - coverage conditions, exclusions, the evidence a claim must carry - frozen and hashed before any claim arrives. A claimant submits a claim binding that version and every document to the hash of its exact bytes. In one consensus round each validator fetches and hashes the documents itself and judges whether the evidence meets each condition, quoting the words it relies on; every quote is re-checked against the bytes that node verified. Deterministic code owns deadlines, required evidence, precedence, any parametric threshold and every reliance gate, and names the verdict: supported, not established, exclusion applies, fraud indicators, inconclusive or evidence unavailable. Evidence that instructs its reader cannot win coverage, and nothing moves money. Verified with 233 tests, a mutation sweep, a live suite and a FINALIZED deployment identical to source.

(996 characters.)
