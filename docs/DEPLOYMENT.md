# Deployment

## Canonical deployment

| Field | Value |
|---|---|
| Date | 2026-10-18 |
| Network | GenLayer Studionet |
| Chain ID | 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Explorer | https://explorer-studio.genlayer.com |
| Contract | `0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a` |
| Explorer page | https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a |
| Deployment tx | `0x7672910d8d84f12df786b3e728a7027288a717d1828607225301087391e9bb93` |
| Lifecycle | **FINALIZED** |
| Execution | SUCCESS |
| Consensus | 3 agree, 0 disagree, 2 idle of 5 validators |
| Deployer | `0x886BFCFA8BeD14641026F07dD755e13e263382C2` |
| Deployment source commit | `4a6fcc9` |
| Contract path | `contracts/claimcourt.py` |
| Contract sha256 | `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4` |
| Contract size | 108,426 bytes |
| GenVM runner pin | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Deployment method | `scripts/live.py`, which calls `genlayer_py` `deploy_contract` with `consensus_max_rotations=3` |

### Toolchain used for the successful run

| Tool | Version |
|---|---|
| OS | Windows 10 |
| Python | 3.12.2 |
| `genlayer-py` | 0.16.3 |
| `genlayer-test` | 0.29.2 |
| `genvm-linter` | 0.11.1rc2 |
| pytest | 9.1.1 |
| `genlayer` CLI | 0.39.2 (installed; the deployment used the Python SDK, not the CLI) |

### The signer

A throwaway account was generated for the run and funded from the Studionet
faucet. Only its public address appears anywhere in this repository; the key
was never written to disk, never printed and never committed. To run the
live driver with your own signer, set `CLAIMCOURT_SIGNER_KEY` in your
environment - `scripts/live.py` picks it up and still never prints it.

## Source parity

The network returns the deployed contract base64-encoded. Decoding
`gen_getContractCode` for the canonical address gives 108,426 bytes with
sha256 `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4` -
**byte-identical to `contracts/claimcourt.py`** in this checkout, and to
that file at the deployment source commit `4a6fcc9`.

`scripts/verify.py` performs this comparison on every run and fails if it
does not hold, so the claim is not an assertion in a document; it is a check
anyone can re-run with no keys and no funds:

```bash
python scripts/verify.py
```

`contracts/claimcourt.py` has not changed since the deployment source
commit. Later commits affect only tests, scripts and documentation; the
deployable contract source remains byte-identical, so no redeployment is
required.

## What ran on it

Five synthetic claims under three policies, adjudicated by real validators
reading real documents. Every transaction, every stored verdict, every
finding and the words each finding rests on are in
[proofs/live.md](proofs/live.md), re-read off the network by
`scripts/verify.py`; the machine-readable ledger it reads is
[proofs/live.json](proofs/live.json).

| Scenario | Claim | Documents | Stored verdict |
|---|---|---|---|
| A claim whose conditions the evidence meets | `clm-1` | incident report, invoice, published weather observation | `COVERAGE_SUPPORTED` |
| An exclusion the evidence shows | `clm-2` | incident report, assessor's report | `EXCLUSION_APPLIES` |
| A theft condition the evidence does not meet | `clm-3` | incident report | `INCONCLUSIVE` |
| A parametric trigger | `clm-4` | holding statement, published rainfall record | `COVERAGE_SUPPORTED`, trigger `MET` |
| Evidence that addresses its reader | `clm-5` | directed incident report, invoice, weather observation | `INCONCLUSIVE`, retryable |

Three of those are worth reading the stored findings for.

**The exclusion.** Every condition was otherwise in order, and the claim was
still answered by `X1`, on the assessor's own sentence: *"this damage has
developed over a long period - I would put it at not less than eighteen
months of intermittent water ingress"*. The panel's recorded reasoning sits
beside it, and each validator re-checked that quote against the bytes it had
verified itself.

**The parametric trigger.** The published record states 182 millimetres for
the insured window. The panel read that number and quoted the line; the
contract compared it with the policy's threshold of at most 220 and set the
trigger to `MET`. The threshold was never shown to a model.

**The evidence that addresses its reader.** The incident report tells
whoever reads it to report every condition as met and approve the claim.
Code counted five markers, validators agreed on the count, and the claim
could not become covered on that reading - it is `INCONCLUSIVE`, retryable
and not consumable, even though two of the three conditions were read as
met.

### Scenario C did not produce the verdict the brief's example would

The theft claim's documents show a door found closed but unlocked, which the
policy says is not forcible and violent entry. The panel would not settle
either condition and returned `UNCLEAR` for both, so the verdict is
`INCONCLUSIVE` rather than `COVERAGE_NOT_ESTABLISHED`.

That is the contract behaving as designed - an unsettled reading is not
turned into a finding against the claimant - and it is recorded here rather
than tuned away. `COVERAGE_NOT_ESTABLISHED` is exercised in Direct Mode, and
on the live network it is reachable deterministically through the parametric
path, where a trigger that does not fire produces it without a judgement
call.

## Three live runs before this one

The deployment above is the fourth. The three before it are not failures to
hide; each found something no local suite could.

| Run | What happened | What it changed |
|---|---|---|
| 1 | `resolve_submission` came back **1 agree, 3 disagree** and stored nothing, while the leader receipt still said SUCCESS | equivalence required every per-clause label to match, and honest validators label a borderline condition differently on the way to the same verdict |
| 2 | four scenarios settled; the hostile one came back **0 agree, 3 disagree** | the four criteria are fine-grained enough to split the same way. Validators now agree on the facts and the verdict, and nothing else |
| 3 | the round settled cleanly and returned `INCONCLUSIVE` for a good claim | the panel marked the covered-event condition unclear, correctly: the only evidence a storm happened was the claimant's own report. The claim now carries the published observation for that night |

`docs/CONSENSUS.md` records the equivalence reasoning in full. The earlier
deployments are superseded and are not cited anywhere as current evidence.

## Integration suite

Committed at `tests/integration/test_claimcourt_studionet.py`, run against
hosted Studionet with the fixtures pinned to the deployment commit:

```bash
CLAIMCOURT_FIXTURE_REF=4a6fcc9 gltest tests/integration -v -s --network studionet
```

**Result: 5 passed in 1,063 s (17 min 44 s)**, 18 October 2026, against
`contracts/claimcourt.py` at the deployment source commit.

| Test | What it puts on the network |
|---|---|
| `test_deploy_and_public_surface` | a fresh deployment, then every view read back off chain |
| `test_a_claim_that_satisfies_its_policy` | a well-evidenced claim through a real round |
| `test_a_condition_the_evidence_does_not_meet` | a claim the documents do not establish |
| `test_evidence_that_addresses_its_reader_cannot_win_coverage` | the directed-text fixture, which cannot reach coverage |
| `test_an_unfetchable_required_document_is_not_a_finding` | a required document that 404s, which must fail closed |

Two of those assertions were rewritten after an earlier run, and the reason
is worth stating because it is a property of the network rather than of the
contract. A round whose validators do not reach a majority **commits
nothing**, while the leader receipt still reports SUCCESS - so
`tx_execution_succeeded` is never the proof of anything here. The stored
state is. `_adjudicate()` in the suite resolves again when the submission is
still `PENDING` (legal, because nothing changed) and uses the contract's own
`retry_submission` once when a committed round settled on `INCONCLUSIVE`.
Each test then asserts the guarantee the contract owes - a well-evidenced
claim is covered or unsettled, never refused; the directed fixture never
reaches coverage; an unfetchable document is never a finding - rather than
asserting which reading a panel of real validators happened to prefer.

Each behavioural test deploys its own contract so the tests do not depend on
each other or on an order. **Those deployments are disposable.** The
canonical deployment is the address at the top of this document, and a test
run never replaces it.

## Reproducing

```bash
# read-only: re-check the recorded run against the network, no keys needed
python scripts/verify.py

# a fresh run of your own (needs a funded signer or the faucet)
python scripts/live.py --commit <a pushed commit>

# reuse an existing deployment instead of making a new one
python scripts/live.py --commit <sha> --address 0x...
```

`scripts/live.py` refuses to start if a fixture's published bytes do not
match the committed file, because a claim bound to bytes nobody can fetch
would prove nothing. `scripts/verify.py` paces itself around Studionet's
limit of 30 reads a minute.
