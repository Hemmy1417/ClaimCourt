# Submission notes

Copy-ready. Every number here is one a command in this repository printed;
nothing is estimated.

## Identity

| Field | Value |
|---|---|
| Category | Standalone GenLayer Intelligent Contract |
| Title | ClaimCourt — review of a stated denial against the rule it cites |
| Repository | https://github.com/Hemmy1417/ClaimCourt |
| Licence | MIT |
| Network | GenLayer Studionet, chain 61999 |

**One-line thesis.** ClaimCourt is a reusable GenLayer Intelligent Contract
that decides, under validator consensus, whether a refusal's stated reasons
are supported by the policy clauses they cite.

## Canonical deployment

| Field | Value |
|---|---|
| Contract | `0x78188E7554564606401b7f3B368076D08e0ef63E` |
| Explorer (portal evidence URL) | https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E |
| Deployment tx | `0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c` |
| Lifecycle | FINALIZED, execution SUCCESS, 3 agree / 0 disagree / 2 idle of 5 |
| Deployment source | commit `0ddcd67`, `contracts/claimcourt.py`, blob `bd2ab2f0ec2ec905482d49b731a5716abdc81f81` |
| Source parity | deployed bytes byte-identical to the committed source (sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9`) |


## Why GenLayer is required

Checking a prose reason against a prose rule is reading, and the party that
wrote the refusal normally controls that reading — its own staff, its own
chosen reviewer, or a model behind its own backend. Remove GenLayer and the
contract loses the only two inputs it cannot compute: whether the cited
clause is in the bound document at all, and whether that clause as written
reaches the ground the notice gave. Keep a single reader instead of
consensus and it loses the ability to tell a true reading from a purchased
one — including against a notice that addresses its reader directly, which
one demonstration fixture does on purpose.

## Consensus mechanism

One `gl.vm.run_nondet_unsafe` round with a custom validator. The leader
fetches both hash-bound documents, hashes them before reading them, counts
text addressed to the reader in code, computes two literal triage bits per
ground, convenes one panel call with `response_format="json"`, reads the
answer strictly, holds every positive answer to a quote from the bytes it
verified, and derives each ground's outcome in code. Each validator
reproduces the entire round from its own fetches and its own panel call,
then gates the leader's payload against its own verified bytes — type by
type, enum by enum, binding by binding, quote by quote — and compares the
decision fields. Reasoning prose and the choice of grounded span may
differ; nothing that decides the verdict may.

## Deterministic responsibilities

Authorisation, identifiers, both document hashes, URL admission, every
bound, the literal triage bits, the directed-text count, quote grounding,
per-ground outcomes, verdict precedence, the directed-text ceiling, status
transitions and terminal replay, the notice registry, counters, freshness
arithmetic and every reliance gate. The model is never asked what the
verdict is, and never asked whether anything should be paid.

## Failure policy

Fail closed throughout. An unfetchable, substituted, oversized or unreadable
document gives `RECORD_UNAVAILABLE`; an unusable panel answer gives
`INCONCLUSIVE`; an ungrounded "located" is not located; an unknown enum or
wrong type is a failure rather than a default; a notice that addresses its
reader cannot be upheld. `is_consumable` is false for every retryable
state, for a withdrawn review, for a revoked clause version and for a stale
one. Retries are capped at three rounds, after which the review resolves
unsettled and is never consumable.

## Reuse surface

`is_denial_supported(review_id, as_of)` is the fail-closed boolean,
`is_denial_unsupported(...)` its counterpart, `review_outcome(...)` the
full picture including the definition hash the verdict was read against,
and `clause_record(clause_set_id, version, clause_ref)` the accumulating
per-clause signal. Three consumers that need no change to the contract:
dispute platforms deciding whether to escalate a refusal, settlement
contracts holding a disputed amount until a refusal fails review, and
conduct monitors watching which clauses produce refusals that keep failing
review.

## Test results

| Gate | Result |
|---|---|
| source invariants (`scripts/preflight.py`) | 131/131 |
| Direct Mode (`pytest tests/direct -q`) | 176 passed, 0 failed, 0 skipped |
| pickling checks | on, passing |
| GenVM AST lint | passed, 3 checks |
| GenVM SDK validation | passed, 28 methods (20 view, 8 write) |
| mutation sweep (`scripts/mutate.py`) | 24/29 killed, 5 equivalent, each argued in `docs/TESTING.md` |

## Live evidence

Twelve transactions, every one FINALIZED with execution SUCCESS, all
re-read off the network by `python scripts/verify.py` (read-only, no keys):

| Scenario | Stored verdict | Gate |
|---|---|---|
| a refusal whose cited clause reaches its ground | `DENIAL_SUPPORTED` | consumable, `is_denial_supported` true |
| a refusal whose cited clause contradicts its ground | `DENIAL_UNSUPPORTED` | consumable, `is_denial_supported` false |
| a refusal citing a clause absent from the wording | `CLAUSE_MISCITED` | `is_denial_supported` false |
| a jewellery-only limit used to refuse a whole claim | `DENIAL_UNSUPPORTED` | consumable, `is_denial_supported` false |
| a refusal whose notice instructs whoever reads it | `INCONCLUSIVE`, retryable | every gate false, nothing added to any clause record |

Three of the five readings carry a dissenting validator minority while the
majority carried - validators deciding rather than deferring.
`DENIAL_OVERBROAD` is exercised in Direct Mode and has not been produced
live; `docs/DEPLOYMENT.md` records why. Full detail, including the sentences
the panel quoted and each node re-checked: `docs/proofs/live.md`.


## Limitations

Not legal advice, not a regulatory determination, not an ombudsman
decision, and no verdict obliges anyone to pay anything.
`DENIAL_UNSUPPORTED` says a stated reason did not stand up on the two
documents reviewed — not that the claim is valid. `DENIAL_SUPPORTED` says
the stated reasons stood up as written — not that the decision was fair or
lawful. The contract cannot tell whether published wording is the wording a
claimant bought. URL rules are defence in depth, not SSRF prevention.
Prompt-injection handling is layered, not immune. Documents must be public,
because a validator has to fetch them. Studionet deployment for
demonstration and reuse, not an audited production system. Every fixture is
synthetic and labelled.

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
app, no frontend and no user journey: the deliverable is one deployed
contract and the evidence that it does what it says.

The portal validates one evidence URL specifically as
`genlayer-explorer-contract`. For a Studionet contract that is the Explorer
**address** page - not the repository, not a transaction, not the Studio
import link:

```text
https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E
```

Supporting evidence, where the form allows more than one link:

| What | URL |
|---|---|
| Repository | https://github.com/Hemmy1417/ClaimCourt |
| Deployment evidence | https://github.com/Hemmy1417/ClaimCourt/blob/main/docs/DEPLOYMENT.md |
| Live run, re-read off chain | https://github.com/Hemmy1417/ClaimCourt/blob/main/docs/proofs/live.md |

**Title**

```text
ClaimCourt - review of a stated denial against the rule it cites
```

**Description** - the measured block under "Portal description" below, 971
characters.

**One-liner**, if the form asks for one (173 characters):

```text
Reviews whether a refusal's stated reasons are supported by the policy clauses they cite, under validator consensus, and records a typed verdict other contracts can rely on.
```

**Verification outcome**, if the form asks for one (450 characters):

```text
Open the contract on the explorer and read any review: it stores the verdict, each ground's outcome, and the sentences quoted from both documents. The wording and the notice are each bound to the hash of their exact bytes, so anyone can fetch them, hash them, and confirm what was read. A read-only script in the repository re-queries every transaction and re-reads every stored result, and the deployed contract decodes back to the committed source.
```

No addresses, hashes, identifiers or shell commands appear in any text
field; the contract address belongs only in the validated evidence URL.

**Contribution date** is the day you submit, not the build date.

A 512px raster of the mark is at `docs/assets/claimcourt-mark-512.png` if the
form asks for an image. The seven-step "how to use it" walkthrough and the
live-site evidence row that a Project submission wants do not apply here.
If the form shows fields this section does not cover, tell me what it asks
for and I will measure the text for them.

## Portal description (under 1000 characters)

ClaimCourt is a standalone GenLayer Intelligent Contract that reviews a refusal against the rule it cites. A decider publishes wording, bound to the hash of its exact bytes. Anyone opens a review of a refusal notice, also hash-bound, naming each clause cited and each ground given. In one consensus round every validator fetches and hashes both documents itself and judges whether the clause as written reaches that ground, re-checking every quote against the bytes it verified, so nothing invented survives. Deterministic code owns authorisation, versioning, precedence and every reliance gate, and names the verdict: supported, unsupported, overbroad, miscited, misstated, inconclusive or unavailable. A notice that instructs its reader cannot be upheld. Consumers read one boolean, and a per-clause record accumulates. Verified with 176 Direct Mode tests, GenVM validation, a mutation sweep, a live suite, and a FINALIZED Studionet deployment byte-identical to source.

(971 characters.)
