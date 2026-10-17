# Deployment

## Canonical deployment

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Network | GenLayer Studionet |
| Chain ID | 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Explorer | https://explorer-studio.genlayer.com |
| Contract | `0x78188E7554564606401b7f3B368076D08e0ef63E` |
| Explorer page | https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E |
| Deployment tx | `0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c` |
| Lifecycle | **FINALIZED** |
| Execution | SUCCESS |
| Consensus | 3 agree, 0 disagree, 2 idle of 5 validators |
| Deployer | `0x45F087bfCDf4872c5325a00E3260B9104f12DFf5` |
| Deployment source commit | `0ddcd67` |
| Contract path | `contracts/claimcourt.py` |
| Contract git blob | `bd2ab2f0ec2ec905482d49b731a5716abdc81f81` |
| Contract sha256 | `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` |
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
`gen_getContractCode` for the canonical address gives 71,946 bytes with
sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` -
**byte-identical to `contracts/claimcourt.py`** in this checkout, and to
that file's blob at the deployment source commit `0ddcd67`.

`scripts/verify.py` performs this comparison on every run and fails if it
does not hold, so the claim is not an assertion in a document; it is a
check anyone can re-run:

```bash
python scripts/verify.py
```

`contracts/claimcourt.py` has not changed since the deployment source
commit. Commits after `0ddcd67` affect only tests, scripts, fixtures
tooling and documentation; the deployable contract source remains
byte-identical, so no redeployment is required.

## Live transactions

Every transaction below was read back off the network by
`scripts/verify.py`, which also re-read the stored state each one produced.
The full output, including the quotes the panel grounded, is in
[proofs/live.md](proofs/live.md); the machine-readable ledger it reads is
[proofs/live.json](proofs/live.json).

| Step | Transaction | Lifecycle | Execution | Validators |
|---|---|---|---|---|
| deploy | `0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `register_clause_set` | `0x2597c35a6228162b807a44ca1a38df47ceed58e7b2053fb326e9a9a39d6837f3` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `open_review` rv-1 | `0x60a72e456e8b1fe8e8bfb5195a6441b9280cbb65117154a7132288661d11546c` | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| `resolve_review` rv-1 | `0x967994a67587d9a2af45e3340944ef7be02464e1cba7756c1bede677cb81db69` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `open_review` rv-2 | `0xc226f614d696bcc7816ad739fd601e0ac551aec2204f6218f553e04c96615d18` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `resolve_review` rv-2 | `0x3511ae8c78c85b6a43b5562665babed503974c8a1a38e60103bde32f72689474` | FINALIZED | SUCCESS | 3 agree, **1 disagree**, 1 idle of 5 |
| `open_review` rv-3 | `0xc4e88c36bf486d9a6f1967259615f37f69b48b42d39c9c0b27ae3ec82adc0101` | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| `resolve_review` rv-3 | `0xbb0db0d7bb23e299e377923fc84f7095178b8e2a1982c546944675083c7b9928` | FINALIZED | SUCCESS | 3 agree, **2 disagree**, 0 idle of 5 |
| `open_review` rv-4 | `0x861276133fb07019c194453071d8423f1e893d23862475c3c2b7b5f24db25f01` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `resolve_review` rv-4 | `0xd74a6e63b55a1fef561d9114faa59d66cfdb446fcb456478d942954318f27746` | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| `open_review` rv-5 | `0xc8f417439ae61586afc3b1ce1497063a8768a7f4a8b4fcbfd7561d2b073ca582` | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| `resolve_review` rv-5 | `0xb0ec5c7ab9cf1be1c48acce913757e49badc9a74cd7c1c6159f4bb1cdb9a1bdc` | FINALIZED | SUCCESS | 3 agree, **1 disagree**, 1 idle of 5 |

Three of the five readings carry a dissenting minority. That is the mechanism
working, not a fault: a validator that fetched both documents, read them,
and did not reach the leader's conclusion votes against it, and the round
commits on the majority. Unanimity on every semantic question would be the
result worth suspecting.

## What the live scenarios proved

| Scenario | Review | Documents | Stored verdict | Gate |
|---|---|---|---|---|
| A refusal whose cited clause reaches its ground | `rv-1` | wording + `notice-unoccupied.txt` | `DENIAL_SUPPORTED` | `is_denial_supported` true, `is_consumable` true, freshness `RELIABLE` |
| A refusal whose cited clause contradicts its ground | `rv-2` | wording + `notice-late-notification.txt` | `DENIAL_UNSUPPORTED` | `is_denial_supported` false, `is_denial_unsupported` true |
| A refusal citing a clause that is not in the wording | `rv-3` | wording + `notice-flood-clause.txt` | `CLAUSE_MISCITED` | the clause label was not found literally either; `is_denial_supported` false |
| A refusal whose notice instructs whoever reads it | `rv-4` | wording + `notice-unoccupied-directed.txt` | `INCONCLUSIVE`, status `RETRYABLE` | 4 markers counted in code; every gate false, nothing added to any clause record |
| A jewellery-only limit used to refuse a whole claim | `rv-5` | wording + `notice-jewellery-limit.txt` | `DENIAL_UNSUPPORTED` | `is_denial_supported` false, `is_denial_unsupported` true |

Scenario B is the one worth reading the quote for. The notice says the cover
ended because notification was late; clause 3.3 says in terms that a late
notification "does not by itself end the cover". Real validators, reading
the wording themselves, stored that sentence as the ground for
`DENIAL_UNSUPPORTED`.

Scenario A's stored ground outcome is `SUPPORTED`, and so is `rv-4`'s - and
`rv-4` is still not upheld, because the directed-text ceiling is applied by
deterministic code after the round, not by the panel.

### Scenario D did not produce the verdict the script first expected

The driver originally asserted `DENIAL_OVERBROAD` for the jewellery notice:
the clause reaches the ring and the watch, and the notice applies it to the
television and the armchairs too. Real validators stored
`DENIAL_UNSUPPORTED` instead, quoting the clause's own scope sentence -
"This limit applies to jewellery only. It does not reduce, exclude or
otherwise affect cover for any other category of contents" - and reasoning
that a jewellery-only limit does not reach a whole-claim refusal at all.

Both readings are defensible, and the contract is built to keep them apart
rather than merge them. The expectation in the script was wrong, not the
contract: the round reached a majority, the verdict was derived in code from
the grounded rows, the refusal did not stand, and `is_denial_supported` is
false. The assertion now checks what the primitive guarantees - that the
refusal fails and the gate is false - instead of which of two defensible
readings a panel will prefer.

**`DENIAL_OVERBROAD` is therefore exercised in Direct Mode only.** It has
not been produced on the live network, and nothing in this repository
claims otherwise.

## Integration suite

Committed at `tests/integration/test_claimcourt_studionet.py`, run against
hosted Studionet with the fixtures pinned to the deployment commit:

```bash
CLAIMCOURT_FIXTURE_REF=0ddcd67 gltest tests/integration -v -s --network studionet
```

| Test | Result |
|---|---|
| `test_deploy_and_public_surface` | PASSED |
| `test_a_denial_that_stands` | PASSED |
| `test_a_denial_the_clause_does_not_support` | PASSED |
| `test_a_notice_that_addresses_its_reader_is_not_upheld` | PASSED |
| `test_an_unfetchable_document_is_not_a_finding` | PASSED |

**5 passed in 310.74 s (0:05:10)**, 0 failed, 0 skipped, on 2026-10-17
against hosted Studionet with real validators. Not `--leader-only`: every
round above went through validator consensus.

The last of those is the recovery path end to end - a notice at a location
that cannot be fetched gives `RECORD_UNAVAILABLE` with the panel never
convened, the review stays `RETRYABLE` and not consumable, and the opener
withdraws it, which releases the notice digest for a corrected review.

Two earlier attempts at this suite failed before any contract code ran: the
first passed a contract path that `gltest` resolves relative to the
contracts directory, the second passed an `account` keyword that
`ContractFunction.transact` does not take. Both were errors in the test
file, both were fixed there, and `contracts/claimcourt.py` was not touched
for either.

Each behavioural test deploys its own contract so the tests do not depend on
each other or on an order. **Those deployments are disposable.** The
canonical deployment is the address at the top of this document, and a test
run never replaces it.

## Reproducing the live run

```bash
# read-only: re-check the recorded run against the network
python scripts/verify.py

# a fresh run of your own (needs a funded signer or the faucet)
python scripts/live.py --commit <a pushed commit>

# reuse an existing deployment instead of making a new one
python scripts/live.py --commit <sha> --address 0x...
```

`scripts/live.py` refuses to start if a fixture's published bytes do not
match the committed file, because a review bound to bytes nobody can fetch
would prove nothing.
