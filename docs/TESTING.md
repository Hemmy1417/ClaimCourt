# Testing

Three gates, and a fourth that tests the tests.

| Gate | Command | Result |
|---|---|---|
| source invariants | `python scripts/preflight.py` | 131/131 |
| Direct Mode | `pytest tests/direct -q` | 183 passed |
| GenVM lint and SDK validation | `genvm-lint lint contracts/claimcourt.py` then `genvm-lint check contracts/claimcourt.py` | lint passed (3 checks); validation passed, 28 methods (20 view, 8 write) |
| mutation sweep | `python scripts/mutate.py` | **29/29 killed**, no survivors |

Two more gates run against the network:

| Gate | Command | What it is |
|---|---|---|
| live evidence, re-read | `python scripts/verify.py` | read-only, no keys. Re-queries every recorded transaction, re-fetches every bound document, re-reads every stored verdict and gate, and proves the deployed bytes are the committed source. Writes `docs/proofs/live.md`. |
| hosted integration | `CLAIMCOURT_FIXTURE_REF=<sha> gltest tests/integration -v -s --network studionet` | five tests, each on its own disposable deployment, through real validators. **5 passed in 310.74 s** on 2026-10-17 |

Both are recorded in `docs/DEPLOYMENT.md` and `docs/proofs/live.md`.

## CI

`.github/workflows/gates.yml` runs preflight, Direct Mode, AST lint and SDK
validation on `ubuntu-latest` for every push and pull request. The Studionet
integration suite is deliberately excluded: it needs a funded signer and it
creates real deployments, which is not something a push should do.

The first run was green, and it proved why `scripts/fetch_genvm_bundle.py`
is there. `genlayer-test` asks GitHub for `genvm-universal.tar.xz`; the
release ships that asset as `genvm-runners-all.tar.xz`. On a warm cache
nothing notices. On a clean runner:

```text
trying .../v0.3.0-rc7/genvm-universal.tar.xz
  not published under that name (404)
trying .../v0.3.0-rc7/genvm-runners-all.tar.xz
seeded genvm-universal-v0.3.0-rc7.tar.xz from genvm-runners-all.tar.xz:
134842512 bytes, 19 entries
```

Without that step every Direct Mode test would error at import - a red build
that says nothing about the contract. That first run: 131/131, 176 passed
(the suite was 176 tests at that commit), lint passed, validation passed
with 28 methods, in 3m19s. The next run, on a warm cache and the full suite:
131/131, **183 passed in 5.65s**, both lint and validation green.

Environment used for the runs above: Windows, Python 3.12.2,
`genlayer-test` 0.29.2, `genlayer-py` 0.16.3, `genvm-linter` 0.11.1rc2,
pytest 9.1.1. `genvm-linter` 0.11.0 cannot validate against the current
runner bundle format, which is why the version is pinned in
`requirements-test.txt`. `check_pickling` is on for every Direct Mode test.

## One host workaround, committed and scoped

Direct Mode does **not** run natively on Windows with `gltest` 0.29.2. Its
loader writes the transaction message to a temp file, binds that file to
fd 0 with `dup2`, closes its own descriptor and then unlinks the path.
POSIX allows unlinking a file another descriptor still references; Windows
does not, so contract loading dies with

```text
PermissionError: [WinError 32] The process cannot access the file because
it is being used by another process
```

before any contract code runs - 176 setup errors, zero of them about this
contract.

`tests/direct/conftest.py` wraps the loader's own helper so that one failed
cleanup is tolerated, and restores `os.unlink` immediately afterwards. It is
guarded by `sys.platform != "win32"`, so it does nothing on Linux or macOS.
The contract is not involved and not modified.

It is **committed**, deliberately: an uncommitted local shim would mean the
suite only passes on one machine, and the clean-clone gate below exists to
catch exactly that. It was caught that way - an earlier version of this
document claimed Direct Mode ran natively, because the `gltest` install on
the build machine had been patched by hand at some point to tolerate the
same unlink. A fresh virtualenv from `requirements-test.txt` proved
otherwise.

## Clean-clone gate

```bash
gh repo clone Hemmy1417/ClaimCourt /tmp/cc-clean && cd /tmp/cc-clean
py -3.12 -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements-test.txt
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/preflight.py
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest tests/direct -q
PYTHONUTF8=1 ./.venv/Scripts/genvm-lint.exe lint contracts/claimcourt.py
```

The clone's `contracts/claimcourt.py` carries git blob
`bd2ab2f0ec2ec905482d49b731a5716abdc81f81` and sha256
`c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` - the
same bytes the canonical deployment holds.

Result, 2026-10-17, against commit `f499f44` in a clone made with
`gh repo clone` and a virtualenv built from `requirements-test.txt`:
preflight **131/131**, Direct Mode **183 passed**, GenVM lint **passed**,
SDK validation **passed** (28 methods), and `scripts/verify.py` **all
checks passed** - the live evidence re-checks from a fresh checkout with no
keys. Before the workaround above was committed, the same clone produced
176 setup errors.

A fresh virtualenv resolves exactly the pinned `genlayer-py` 0.16.3,
`genlayer-test` 0.29.2, `genvm-linter` 0.11.1rc2 and pytest 9.1.1. One
environment prerequisite is not in `requirements-test.txt` and cannot be:
both `gltest` and `genvm-linter` download a GenVM runner bundle into
`~/.cache/` on first use. On a warm cache the gates run offline; on a cold
one the first run fetches it.

## What the Direct Mode suite covers

| File | Tests | What it proves |
|---|---|---|
| `tests/direct/test_lifecycle.py` | 50 | registration and hashing, ownership of versions and revocation, a new version not touching an open review, who may open and withdraw, the notice registry, identifier errors, the URL admission matrix, digest format, bounds on grounds and text, pagination, independent records |
| `tests/direct/test_verdicts.py` | 26 | every verdict, precedence across several grounds, retry to a settled reading, round exhaustion, unavailable and substituted and oversized and empty documents, the directed-text ceiling, terminal replay, the receipt, staleness, revocation, supersession and lineage, counters moving exactly once |
| `tests/direct/test_hardening.py` | 44 | hostile panel output: unusable answers, wrong types, bool-as-int, unknown enums, missing and duplicate and extra fields, fence and prose recovery, enum normalisation, invented quotes, quotes too short to mean anything, quotes from the wrong document, oversized quotes and reasoning, and the marker count |
| `tests/direct/test_validators.py` | 56 | the contract's own validator closure, replayed through `direct_vm.run_validator` against forged leader results - and agreeing with honest ones |
| `tests/direct/test_gate_units.py` | 7 | the gate rules the validator comparison reaches first: a row contradicting its own fields, a finding on a round that did not read, a panel state contradicting the documents, a verdict derived from an unread round or an unexamined document, and a second record against a review that already counted |

Nothing monkeypatches `resolve_review`. The mocks sit on the two document
fetches and the panel call; everything between them is the contract's code.

## The mutation sweep

A green suite says the contract passes its tests. It does not say the tests
would fail if the contract were wrong. `scripts/mutate.py` removes one guard
at a time in a scratch copy and runs the whole Direct Mode suite against it.
A mutation that still passes is a hole in the tests, and is reported as
SURVIVED.

**29 mutations, 29 killed, no survivors.**

What gets broken, and what notices:

| Mutation | Caught by |
|---|---|
| any quote is accepted as grounded | `test_an_invented_clause_quote_cannot_locate_a_clause`, `test_an_invented_quote_is_rejected_even_when_the_outcome_matches` |
| a one-word quote counts | `test_a_quote_too_short_to_mean_anything_does_not_ground` |
| an integer passes for a boolean | the type matrix in `test_hardening.py` and `test_validators.py` |
| an unknown `supported` value is kept | the same matrices |
| the leader names its own outcome | `test_a_row_whose_outcome_contradicts_its_own_fields_is_refused` |
| an unread round may carry findings | `test_a_round_that_did_not_read_cannot_carry_a_finding` |
| the payload need not be bound to this review | `test_a_rebound_payload_is_rejected` |
| the panel state need not match the documents | `test_a_panel_state_that_contradicts_the_documents_is_refused` |
| a notice may address its reader and still be upheld | `test_a_notice_that_addresses_its_reader_cannot_be_upheld` |
| an unread round is treated as a reading | `test_an_unread_round_is_never_a_finding` |
| a misstated ground is outranked | `test_a_misstated_ground_outranks_a_miscited_clause` |
| an undecided ground is upheld | `test_an_unclear_reading_is_inconclusive_and_retryable` |
| an unavailable document is a reading | `test_a_document_that_was_not_examined_is_never_a_finding` |
| the committed hash is not checked | `test_a_substituted_document_is_not_the_document` |
| the size cap is removed | `test_an_oversized_document_is_refused_before_it_is_read` |
| any location is admitted | the URL admission matrix in `test_lifecycle.py` |
| everything the leader says is agreed with | the true-controls and forgeries in `test_validators.py` |
| per-ground findings are not compared | `test_a_forged_conclusion_is_rejected` |
| a leader failure is always believed | `test_a_transient_claim_is_rejected_when_this_node_succeeds` |
| the document statuses are not compared | `test_claiming_a_document_was_read_when_it_cannot_be_fetched` |
| a resolved review can be read again | `test_a_resolved_review_is_terminal` |
| rounds never run out | `test_rounds_run_out_and_the_review_settles_unsettled` |
| anyone may publish a clause version | `test_only_the_owner_publishes_or_revokes` |
| anyone may withdraw another party's review | `test_a_withdrawn_review_releases_its_notice` |
| the same notice can be reviewed twice | `test_the_same_notice_is_reviewed_once` |
| a retried review counts twice | `test_the_same_review_cannot_be_counted_twice` |
| an unsettled review is consumable | the reliance assertions across `test_verdicts.py` |
| a verdict never goes stale | `test_a_verdict_goes_stale_after_its_window` |
| a revoked clause version blocks nothing | `test_revoking_the_version_blocks_its_reviews` |

### The five that used to survive

An earlier sweep killed 24 of 29. The five that survived were all rules the
validator's field-by-field comparison reaches first: remove the rule, and a
forged payload still fails on `_first_difference` before the missing check
would have mattered, so no end-to-end assertion changed.

That is a real argument, but it is an argument rather than a test, and it
does not hold where those rules actually bite: the ratified payload is parsed
once more after consensus, in `_run_round`, with no validator left to compare
against. `tests/direct/test_gate_units.py` now calls `_parse_payload`,
`_derive_verdict` and `_record_outcome` directly with staged inputs, so each
rule is responsible for its own failure. The same five mutations are now
killed:

| Rule | Why it survived before | Test that kills it now |
|---|---|---|
| a row's `outcome` must be the one its own fields derive | `outcome` is also compared against the validator's own row | `test_a_row_whose_outcome_contradicts_its_own_fields_is_refused` |
| an unread round's rows have one permitted shape | every such row differs from the validator's own `UNDECIDED` row | `test_a_round_that_did_not_read_cannot_carry_a_finding` |
| `panel_state` must match the document statuses | all three fields are compared directly | `test_a_panel_state_that_contradicts_the_documents_is_refused` |
| an unread round is never a finding | unread rows are `UNDECIDED`, so the later branch returns the same verdict | `test_an_unread_round_is_never_a_finding` |
| a review contributes to a clause's record once | the counters sit behind a terminal-state guard that no public path can pass twice | `test_the_same_review_cannot_be_counted_twice` |

Each of those tests has a true-control beside it, so a rejection cannot be a
staging error, and `module` is resolved from the deployed class rather than
by name - which is why the sweep, loading a patched copy under its own
module name, exercises them too.

### Re-running it

```bash
python scripts/mutate.py              # all 29
python scripts/mutate.py grounding    # only mutations matching a word
```

The sweep sets `CLAIMCOURT_CONTRACT` so the suite loads the patched copy;
the committed contract is never modified. It takes roughly twenty minutes,
because a surviving mutant costs a full suite run.
