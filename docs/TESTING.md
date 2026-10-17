# Testing

Three gates, and a fourth that tests the tests.

| Gate | Command | Result |
|---|---|---|
| source invariants | `python scripts/preflight.py` | 131/131 |
| Direct Mode | `pytest tests/direct -q` | 176 passed |
| GenVM lint and SDK validation | `genvm-lint lint contracts/claimcourt.py` then `genvm-lint check contracts/claimcourt.py` | lint passed (3 checks); validation passed, 28 methods (20 view, 8 write) |
| mutation sweep | `python scripts/mutate.py` | 24/29 killed, 5 equivalent (below) |

Two more gates run against the network:

| Gate | Command | What it is |
|---|---|---|
| live evidence, re-read | `python scripts/verify.py` | read-only, no keys. Re-queries every recorded transaction, re-fetches every bound document, re-reads every stored verdict and gate, and proves the deployed bytes are the committed source. Writes `docs/proofs/live.md`. |
| hosted integration | `CLAIMCOURT_FIXTURE_REF=<sha> gltest tests/integration -v -s --network studionet` | five tests, each on its own disposable deployment, through real validators. **5 passed in 310.74 s** on 2026-10-17 |

Both are recorded in `docs/DEPLOYMENT.md` and `docs/proofs/live.md`.

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

Nothing monkeypatches `resolve_review`. The mocks sit on the two document
fetches and the panel call; everything between them is the contract's code.

## The mutation sweep

A green suite says the contract passes its tests. It does not say the tests
would fail if the contract were wrong. `scripts/mutate.py` removes one
guard at a time in a scratch copy and runs the whole Direct Mode suite
against it. 24 of 29 mutations were caught. The five that were not are
below, each with the reason - two of them are redundant defences, three are
unreachable by construction, and none of them is a hole where a wrong
answer could be stored.

### 1. `gate: the leader names its own outcome`

Removes the check in `_parse_payload` that each row's `outcome` is the one
`_ground_outcome` derives from that row's own fields.

Survives because `_first_difference` compares `clause_located`,
`ground_stated_in_notice`, `supported`, `scope_exceeded` **and** `outcome`
against the validator's own row. The validator's own row always has a
consistent outcome, so an inconsistent forged row differs on at least one
compared field and is rejected there. `test_validators.py` covers both
halves: `test_a_forged_conclusion_is_rejected` and
`test_a_wrongly_typed_or_unknown_row_field_is_rejected` (which includes an
unknown outcome, and a mismatched `supported`).

The re-derivation still matters where no test can reach it: `_run_round`
parses the **ratified** payload again after consensus, with no validator to
compare against. Keeping it costs one comparison.

### 2. `gate: an unread round may carry findings`

Removes the check that on a round where the panel did not answer, every row
is exactly the shape an unread round is allowed to have.

Survives for the same reason: on such a round the validator's own rows are
all `UNDECIDED` with no quotes, so any forged finding differs on a compared
field. `test_a_forged_panel_state_is_rejected` and
`test_claiming_a_document_is_unavailable_when_it_can_be_read` exercise the
pair of states involved.

### 3. `gate: the panel state need not match the documents`

Removes the consistency check between `panel_state` and the two document
statuses.

Survives because all three fields are in `DECISION_FIELDS` and are compared
directly. Covered by `test_a_forged_panel_state_is_rejected` and
`test_claiming_a_document_was_read_when_it_cannot_be_fetched`.

### 4. `verdict: an unread round is treated as a reading`

Removes the `panel_state != PANEL_READ -> INCONCLUSIVE` branch from
`_derive_verdict`.

Survives because the two routes coincide: when the panel did not read,
every row is `UNDECIDED`, and the later `GROUND_UNDECIDED in outcomes`
branch returns `INCONCLUSIVE` anyway. An unavailable document is caught by
the branch before either. The verdict is the same by either path, which is
why no assertion changes - the explicit branch exists so the rule is
readable, not because the fallback is missing.

### 5. `record: a retried review counts twice`

Removes the `counted` flag that stops a review contributing to the clause
record more than once.

Survives because the counters sit inside the terminal branch of
`_record_outcome`, and both entry points - `resolve_review` and
`retry_review` - reject a review whose status is already `RESOLVED`
(`test_a_resolved_review_is_terminal`,
`test_rounds_run_out_and_the_review_settles_unsettled`). There is no path
that reaches the counters twice for one review, so the flag is belt and
braces. `test_an_unclear_reading_is_inconclusive_and_retryable` pins the
behaviour that matters: a review that is read twice and settles once is
counted once.

### Re-running it

```bash
python scripts/mutate.py              # all 29
python scripts/mutate.py grounding    # only mutations matching a word
```

The sweep sets `CLAIMCOURT_CONTRACT` so the suite loads the patched copy;
the committed contract is never modified. It takes roughly twenty minutes,
because a surviving mutant costs a full suite run.
