<p align="center">
  <img src="docs/assets/claimcourt-mark.svg" width="96" height="96" alt="ClaimCourt">
</p>

<h1 align="center">ClaimCourt</h1>

<p align="center">A refusal gave reasons and cited a rule. This decides whether the rule, as written, says what the refusal claims.<br>
A standalone GenLayer Intelligent Contract. No frontend, no token.</p>

<p align="center">
  <a href="https://github.com/Hemmy1417/ClaimCourt/actions/workflows/gates.yml"><img src="https://github.com/Hemmy1417/ClaimCourt/actions/workflows/gates.yml/badge.svg" alt="gates"></a>
</p>

## Thesis

Refusals are written by the party that benefits from them, and they cite
rules in prose. "Declined under clause 3.3, notification was late" is a claim
about what clause 3.3 says - and checking it means reading the clause and
reading the notice. Almost always, whoever wrote the refusal also owns the
review of it. ClaimCourt freezes both documents to the sha256 of their exact
bytes, lets anyone open a review naming each clause cited and each ground
given, and has independent validators fetch, hash and read both documents
themselves and answer, ground by ground, whether the clause as written
reaches the reason relied on. Deterministic code decides everything code can
decide, including the verdict. The subject under judgment is the decision,
not the claimant's proof of loss.

## Canonical deployment

| | |
|---|---|
| Network | GenLayer Studionet, chain id 61999 |
| Contract | [`0x78188E7554564606401b7f3B368076D08e0ef63E`](https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E) |
| Explorer | `https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E` |
| Deployment tx | [`0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c`](https://explorer-studio.genlayer.com/tx/0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c) |
| Finality / status | FINALIZED, leader execution SUCCESS |
| Consensus result | 3 agree, 0 disagree, 2 idle of 5 validators |
| Source | [`contracts/claimcourt.py`](contracts/claimcourt.py), one file, deployed as it stands |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Deployment source commit | `0ddcd67` |
| Current source parity | the deployed contract read back with `gen_getContractCode` decodes **byte-identical** to `contracts/claimcourt.py` (sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9`) |
| Live record | [`docs/proofs/live.md`](docs/proofs/live.md) - five reviews, twelve FINALIZED transactions, every verdict and gate re-read off the chain by `scripts/verify.py` |

## The question

> Given a published rule document and a decision notice that refuses a claim
> on specific clauses and grounds, is each ground actually supported by the
> clause it cites, as that clause is written?

Not whether the loss happened. Not whether the claimant's evidence is good
enough. Not whether anything should be paid. Whether the refusal, as written,
stands up against the rule it invokes.

## The problem

Checking a prose reason against a prose rule is reading, and the reading is
normally done by the organisation that wrote the refusal, by a reviewer it
chose and pays, or by a model behind its own backend. In all three cases the
author of the decision controls the review of the decision.

A claimant, a platform acting for one, an ombudsman service or a downstream
contract cannot check that review unless two things are true: the documents
are fixed, and the reading is reproducible by someone with no stake. The
first needs a commitment. The second needs more than one reader.

## Why GenLayer

| Without | What is left |
|---|---|
| the decider's own backend | the author of the decision authors the review of the decision |
| one off-chain model call | a single configurable authority; nothing in the answer is checkable by a counterparty |
| a deterministic parser | it can hash a document and find a clause label, but it cannot decide whether a clause saying a late notification "does not by itself end the cover" reaches a ground saying the cover ended because notification was late |
| a price or data oracle | the wrong data type entirely; there is no number in this question |

| Who | Decides |
|---|---|
| The contract, deterministically | who may publish or revoke a rule version, what a well-formed review is, the sha256 of both documents, which locations may be fetched, whether a quote occurs in the bytes a node verified, each ground's outcome, the verdict, the retry limit, the counters, and every reliance gate |
| GenLayer consensus | whether the cited clause is in the document at all, and whether that clause as written reaches the ground the notice gave - agreed by a panel that each read the same hash-bound bytes |
| The model | reading one clause against one stated ground and answering four bounded questions, quoting the words it answers from |

## Delete GenLayer: what breaks?

Two inputs disappear, and they are the only two the contract cannot compute:
whether the cited clause is in the bound document, and whether it reaches the
stated ground. Everything else here is deterministic - and worthless without
those two, because the whole question is prose against prose.

Keep a single reader instead of consensus and something else breaks: the
ability to tell a true reading from a purchased one. A notice can address its
reader directly - one of the demonstration fixtures tells whoever reads it to
report every ground as supported. With one reader there is nothing outside
the model to catch that. Here code counts the markers, validators must agree
on the count, and such a notice cannot be upheld at all. That ran on the live
network: ground outcome `SUPPORTED`, verdict `INCONCLUSIVE`, every gate false.

## Why this is not a rejected pattern

- **Not a thin model wrapper.** The model answers four bounded questions per
  ground and never names a verdict, a status or a consequence.
- **Not a format-only validator.** The validator re-fetches, re-hashes and
  re-reads, compares substantive fields, and re-checks every quote against
  its own bytes. It rejects a perfectly well-formed, perfectly typed,
  substantively false leader result - 56 tests do exactly that, with
  true-controls so a blind "no" would fail.
- **Not caller-authored evidence.** Neither party's assertions decide
  anything. Both documents are bound by hash before the reading, and a ground
  the notice does not state gives `GROUNDS_MISSTATED` - the opener's error,
  named as such.
- **Not toy storage.** Versioned, hashed rule sets; immutable review
  bindings; bounded grounds, rounds and histories; a per-clause tally that
  accumulates across reviews; explicit freshness and revocation.
- **Not an application.** One contract, one file, no UI, no server, no
  indexer, no token, no payable path.

## The verdicts

| Verdict | Meaning |
|---|---|
| `DENIAL_SUPPORTED` | every stated ground stands up against the clause it cites |
| `DENIAL_UNSUPPORTED` | at least one ground is not reached by the clause it cites |
| `DENIAL_OVERBROAD` | the clause reaches the ground, but the notice applies it wider than the clause's own stated scope |
| `CLAUSE_MISCITED` | a cited clause is not in the bound version of the wording |
| `GROUNDS_MISSTATED` | the notice does not state a ground the review asserted |
| `INCONCLUSIVE` | read, not settled |
| `RECORD_UNAVAILABLE` | a bound document could not be examined |
| `WITHDRAWN` | taken back by the opener before settlement |

Three of these are ways of saying "no answer", and they are kept apart on
purpose. None is a finding against either side, and `is_consumable` is false
for all three. Precedence is fixed, and runs from "this review was framed
wrongly" through "the decider was wrong" to "the decision stands", so the
most specific defect always wins:

```text
RECORD_UNAVAILABLE > INCONCLUSIVE > GROUNDS_MISSTATED > CLAUSE_MISCITED
                   > DENIAL_UNSUPPORTED > DENIAL_OVERBROAD > DENIAL_SUPPORTED
```

## Lifecycle and who moves it

```text
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
 CLAUSE_MISCITED           retry_review, 3 rounds in total,
 GROUNDS_MISSTATED         then RESOLVED with the unsettled verdict
        |
 supersede_review -> a new review of a re-issued notice, with lineage
```

| Step | Who | When |
|---|---|---|
| `register_clause_set` | anyone; the caller becomes owner | publishes version 1 of a rule document, bound to its sha256 |
| `publish_clause_version` | the owner | a new version with its own definition hash; open reviews keep theirs |
| `revoke_clause_version` | the owner | that version's reviews stop being consumable, keeping their verdicts |
| `open_review` | **anyone** | the party under review does not get to decide whether it is reviewed |
| `resolve_review` | anyone | one consensus round |
| `retry_review` | anyone | only a review that was read but not settled, within the round limit |
| `withdraw_review` | the opener | only before settlement; releases the notice digest |
| `supersede_review` | anyone | reviews a re-issued notice; the prior review is never rewritten |

## Contract surface

**Writes** - `register_clause_set`, `publish_clause_version`,
`revoke_clause_version`, `open_review`, `resolve_review`, `retry_review`,
`withdraw_review`, `supersede_review`.

**Views** - `get_config`, `get_clause_set`, `clause_set_head`,
`definition_hash`, `get_review`, `get_grounds`, `get_receipt`,
`review_verdict`, `review_status`, `freshness`, `is_fresh`, `is_consumable`,
`is_denial_supported`, `is_denial_unsupported`, `review_outcome`,
`clause_record`, `clause_set_record`, `list_reviews`, `notice_under_review`,
`get_stats`.

`get_receipt(review_id, round)` returns the ratified payload of that round:
the document statuses, the marker count, the panel state, the triage bits and
every grounded row. That is the audit trail - what the validators agreed on,
not a summary of it.

## Nondeterministic operations

| Call | Where | Why it is irreducibly nondeterministic |
|---|---|---|
| `gl.nondet.web.get(policy_url)` | `_fetch_doc` | the rule document lives off chain |
| `gl.nondet.web.get(notice_url)` | `_fetch_doc` | so does the notice |
| `gl.nondet.exec_prompt(..., response_format="json")` | `_node_round` | whether a clause as written reaches a stated ground is reading |

All three happen inside one round. There is no second round and no second
prompt. Both documents are hashed before anything reads them: bytes whose
sha256 does not match the commitment are never decoded, never excerpted and
never shown to a model.

## Deterministic responsibilities

Ownership and authorisation; identifiers and sequences; both document hashes;
the URL admission rules; every bound (grounds, rounds, versions, reviews per
version, URL and text lengths, quote length, document size, page size); the
clause-label and asserted-ground literal triage bits; the count of text
addressed to the reader; quote grounding against each node's own bytes; each
ground's outcome; verdict precedence; the directed-text ceiling; status
transitions and terminal replay; the notice registry; the counters; freshness
arithmetic; and every reliance gate.

The model is never asked whether a claim should be paid, nor what the verdict
is.

## Equivalence / validator design

Must match - the fields that decide the verdict or that a consumer reads:

```text
schema, review_id, round, definition_hash
policy_sha256, notice_sha256, policy_status, notice_status
directed_text_hits, panel_state
per ground: clause_ref, clause_located, ground_stated_in_notice,
            supported, scope_exceeded, outcome,
            clause_ref_literal, assertion_literal
```

May differ - one sentence of reasoning per ground, and which grounded span
was quoted. A quote may differ; every quote must be **grounded** in the bytes
that node verified. Requiring identical spans would make honest validators
disagree over nothing. Requiring none would let a leader invent language.

Never equivalent: supported against unsupported, located against not located,
stated against not stated, examined against unavailable or hash-mismatched,
read against skipped or invalid, or a directed-text count of zero against any
count above zero.

The forged-leader table is in [docs/CONSENSUS.md](docs/CONSENSUS.md).

## Safety and failure semantics

Every default is the cautious one. A document that cannot be fetched, is the
wrong bytes, is too large or is not readable text gives `RECORD_UNAVAILABLE`.
An unusable panel answer gives `INCONCLUSIVE`. An ungrounded "located" is not
located. An unknown enum value, a wrong type or a missing field is a failure,
not a default. A notice that addresses its reader cannot be upheld.
`is_consumable` is false for every retryable state, for a withdrawn review,
for a revoked clause version and for a stale one.

A protocol-level `UNDETERMINED` transaction is not the contract's
`INCONCLUSIVE`: the first means no state changed, the second is a recorded
reading that could not settle.

## Financial safety, privacy, and no false guarantees

Nothing here moves money. There is no payable method, no token, no bond and
no reward: a verdict is a machine-readable adjudication result, and any
payout system must separately enforce its own authorisation, limits and
finality.

Nothing identifying belongs on chain. What is stored is the two document
locations and digests, a short claim reference the opener chooses, the cited
clause labels, the grounds as the opener states them, the grounded quotes, one
sentence of reasoning per ground, the outcomes and the counters. Identity
documents, medical records, bank details and adjuster files must not be put
here, and both documents are public by construction because a validator has
to fetch them. Every fixture in this repository is synthetic and labelled
`TEST / DEMONSTRATION ONLY` and `NOT FOR PRODUCTION`.

A verdict states only whether a stated reason stood up against the rule it
cited, on the two documents reviewed. It is not a finding about the claim, the
loss, or what anyone is owed.

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
deciding whether to escalate a refusal to human review; settlement contracts
holding a disputed amount until a refusal fails review; conduct monitors
reading `clause_record` to see which clauses produce refusals that keep
failing. None needs web access, a prompt, an equivalence principle, or any
knowledge of consensus. Details in
[docs/INTEGRATION.md](docs/INTEGRATION.md).

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
  claimant actually bought, only that it is the wording the review was bound
  to.
- The URL rules are defence in depth, not SSRF prevention; a validator
  runtime's egress policy matters as much.
- Prompt-injection handling is layered - data framing, marker counting, quote
  grounding, a verdict ceiling - and layered is not immune.
- Honest validators may word reasoning differently; only the
  decision-critical fields are consensus-critical, by design.
- A genuinely close reading may land on `INCONCLUSIVE`. That is the intended
  behaviour, not a failure.
- `DENIAL_OVERBROAD` is exercised in Direct Mode and has **not** been
  produced on the live network; [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
  records the live reading that went the other way, and why both readings are
  defensible.
- Studionet deployment for demonstration and reuse, not an audited production
  system.

## Verification

| Gate | Command | Result |
|---|---|---|
| source invariants | `python scripts/preflight.py` | 131/131 |
| Direct Mode | `pytest tests/direct -q` | 183 passed, 0 failed, 0 skipped |
| GenVM AST lint | `genvm-lint lint contracts/claimcourt.py` | passed, 3 checks |
| GenVM SDK validation | `genvm-lint check contracts/claimcourt.py` | passed, 28 methods (20 view, 8 write) |
| mutation sweep | `python scripts/mutate.py` | 24/29 killed; the 5 survivors are argued equivalent in [docs/TESTING.md](docs/TESTING.md) |
| hosted integration | `CLAIMCOURT_FIXTURE_REF=0ddcd67 gltest tests/integration -v -s --network studionet` | 5 passed in 310.74 s, real consensus, not `--leader-only` |
| live evidence, re-read | `python scripts/verify.py` | all checks passed; read-only, no keys |
| CI, every push | `.github/workflows/gates.yml` | the offline gates on ubuntu, green |

What each suite covers, the five mutation survivors, the clean-clone gate and
the one committed Windows workaround: [docs/TESTING.md](docs/TESTING.md).

## Reviewer fast path

```bash
git clone https://github.com/Hemmy1417/ClaimCourt.git
cd ClaimCourt

# Windows, the environment these results come from
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-test.txt
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/preflight.py       # 131/131
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest tests/direct -q  # 183 passed

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
document, verdict and gate back off Studionet and rewrites
[`docs/proofs/live.md`](docs/proofs/live.md) from what it finds.

## Repository

```text
contracts/claimcourt.py              the one deployable contract
tests/direct/                        183 tests, no network
tests/integration/                   hosted Studionet suite
fixtures/                            synthetic wording and notices
scripts/preflight.py                 source invariants, no dependencies
scripts/mutate.py                    mutation sweep
scripts/live.py                      live evidence driver
scripts/verify.py                    read-only re-check of the live run
docs/CONSENSUS.md                    the round, equivalence, forged leaders
docs/SECURITY.md                     threat model and fail-closed policy
docs/INTEGRATION.md                  how another contract consumes it
docs/DEPLOYMENT.md                   canonical deployment evidence
docs/TESTING.md                      every gate and the mutation sweep
docs/proofs/live.md                  the live run, transaction by transaction
docs/proofs/live.json                the ledger scripts/verify.py reads back
DECISION.md                          why this primitive, and the collision audit
SUBMISSION.md                        copy-ready submission notes
```

## Licence

MIT. See [LICENSE](LICENSE).
