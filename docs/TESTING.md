# Testing

| Gate | Command | Result |
|---|---|---|
| source invariants | `python scripts/preflight.py` | 167/167 |
| Direct Mode | `pytest tests/direct -q` | 233 passed |
| GenVM lint and SDK validation | `genvm-lint lint contracts/claimcourt.py` then `genvm-lint check contracts/claimcourt.py` | lint passed (3 checks); validation passed, 29 methods (20 view, 9 write) |
| mutation sweep | `python scripts/mutate.py` | <!-- SWEEP --> |

Two more gates run against the network:

| Gate | Command | What it is |
|---|---|---|
| live evidence, re-read | `python scripts/verify.py` | read-only, no keys. Re-queries every recorded transaction, re-fetches every bound document, re-reads every stored verdict, criterion and quoted finding, and proves the deployed bytes are the committed source. Writes `docs/proofs/live.md`. |
| hosted integration | `CLAIMCOURT_FIXTURE_REF=<sha> gltest tests/integration -v -s --network studionet` | five tests, each on its own disposable deployment, through real validators |

Both are recorded in `docs/DEPLOYMENT.md` and `docs/proofs/live.md`.

Environment used for the runs above: Windows, Python 3.12.2,
`genlayer-test` 0.29.2, `genlayer-py` 0.16.3, `genvm-linter` 0.11.1rc2,
pytest 9.1.1. `genvm-linter` 0.11.0 cannot validate against the current
runner bundle format, which is why the version is pinned in
`requirements-test.txt`. `check_pickling` is on for every Direct Mode test.

## CI

`.github/workflows/gates.yml` runs preflight, Direct Mode, AST lint and SDK
validation on `ubuntu-latest` for every push and pull request. The Studionet
integration suite is deliberately excluded: it needs a funded signer and it
creates real deployments, which is not something a push should do.

The first run proved why `scripts/fetch_genvm_bundle.py` ships with it.
`genlayer-test` asks GitHub for `genvm-universal.tar.xz`; the release ships
that asset as `genvm-runners-all.tar.xz`. On a warm cache nothing notices.
On a clean runner:

```text
trying .../v0.3.0-rc7/genvm-universal.tar.xz
  not published under that name (404)
trying .../v0.3.0-rc7/genvm-runners-all.tar.xz
seeded genvm-universal-v0.3.0-rc7.tar.xz from genvm-runners-all.tar.xz:
134842512 bytes, 19 entries
```

Without that step every Direct Mode test would error at import - a red build
that says nothing about the contract.

## One host workaround, committed and scoped

Direct Mode does **not** run natively on Windows with `gltest` 0.29.2. Its
loader writes the transaction message to a temp file, binds that file to
fd 0 with `dup2`, closes its own descriptor and then unlinks the path. POSIX
allows unlinking a file another descriptor still references; Windows does
not, so contract loading dies with

```text
PermissionError: [WinError 32] The process cannot access the file because
it is being used by another process
```

before any contract code runs - every test erroring at setup, none of it
about this contract.

`tests/direct/conftest.py` wraps the loader's own helper so that one failed
cleanup is tolerated, and restores `os.unlink` immediately afterwards. It is
guarded by `sys.platform != "win32"`, so it does nothing on Linux or macOS -
which the CI runs confirm. The contract is not involved and not modified.

It is **committed**, deliberately: an uncommitted local shim would mean the
suite only passes on one machine, and the clean-clone gate exists to catch
exactly that. It was caught that way on an earlier build in this repository,
where the `gltest` install on the build machine had been patched by hand to
tolerate the same unlink.

## Clean-clone gate

```bash
gh repo clone Hemmy1417/ClaimCourt /tmp/cc-clean && cd /tmp/cc-clean
py -3.12 -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements-test.txt
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/preflight.py
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest tests/direct -q
PYTHONUTF8=1 ./.venv/Scripts/genvm-lint.exe lint contracts/claimcourt.py
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/verify.py
```

<!-- CLEANCLONE -->

One environment prerequisite is not in `requirements-test.txt` and cannot
be: both `gltest` and `genvm-linter` download a GenVM runner bundle into
`~/.cache/` on first use. On a warm cache the offline gates run offline; on
a cold one the first run fetches it, and `scripts/fetch_genvm_bundle.py`
seeds it from whichever asset the release actually publishes.

## What the Direct Mode suite covers

| File | Tests | What it proves |
|---|---|---|
| `tests/direct/test_lifecycle.py` | 70 | registration and the policy hash over the whole definition, the definition and trigger admission matrices, URL and digest admission, ownership of versions and challenges, a new version not touching a submitted claim, revocation, challenge admission, the claim deadline, required evidence kinds, incident and evidence admission, duplicate detection, the evidence registry, pagination, truncation |
| `tests/direct/test_verdicts.py` | 25 | every verdict, precedence, the parametric trigger met and not met and unreadable, fraud only where the policy asks and only with the words, retry to a settled reading, round exhaustion, unavailable and substituted and oversized and unreadable documents, the directed-text ceiling, terminal replay, cancellation, the receipt, staleness, revocation, counters moving once |
| `tests/direct/test_hardening.py` | 50 | hostile panel output: unusable answers, wrong row counts, rows out of order, wrong types, bool-as-int, unknown findings, missing sections, fence and prose recovery, normalisation, invented quotes in both directions, quotes from the wrong document, ungrounded exclusions and contradictions, invented measurements, unknown fraud findings, and an answer to a question nobody asked |
| `tests/direct/test_validators.py` | 72 | the contract's own validator closure, replayed through `direct_vm.run_validator` against forged leader results - and agreeing with honest ones, including a differently-labelled route to the same verdict, and the two coherent forgeries that only the verdict and the policy-failure reason can refuse |
| `tests/direct/test_gate_units.py` | 16 | the gate rules the validator comparison reaches first, each staged so exactly one rule stands between the payload and acceptance |

Nothing monkeypatches `resolve_submission`. The mocks sit on the document
fetches and the panel call; everything between them is the contract's code.

## The mutation sweep

A green suite says the contract passes its tests. It does not say the tests
would fail if the contract were wrong. `scripts/mutate.py` removes one guard
at a time in a scratch copy and runs the whole Direct Mode suite against it.
A mutation that still passes is a hole in the tests, and is reported as
SURVIVED.

<!-- SWEEPDETAIL -->

### What earlier sweeps caught

Four mutations survived earlier rounds of this build, and every one was a
staging error of the same kind: the payload a test handed the gate was being
refused by a *different* rule before it reached the rule under test, so
removing that rule changed nothing.

| Survivor | Why the test never reached it |
|---|---|
| an unassessed round may carry findings | the exclusions branch rejected the payload before the conditions branch mattered |
| the panel state need not match the record | the outcome-consistency rule rejected it first |
| the trigger state is taken on trust | staged on a policy that declares no trigger, where a different rule refuses any state but `NOT_DECLARED` |
| the missing kinds are taken on trust | the staged list agreed with the rows, so it never tested the derivation |

Plus one rule with no test at all: the 200,000-byte document cap. All five
are now covered, each staged so that exactly one rule stands between the
payload and acceptance.

### Re-running it

```bash
python -u scripts/mutate.py > sweep.log     # all of them
python scripts/mutate.py grounding          # only mutations matching a word
```

The sweep sets `CLAIMCOURT_CONTRACT` so the suite loads the patched copy;
the committed contract is never modified. Send the output straight to a
file: piping it through another process buffers the progress away, and a
background limit can then kill it with nothing to show.
