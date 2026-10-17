# Live evidence

Written by `python scripts/verify.py`, which reads everything below off GenLayer Studionet. Nothing here is a transcript: re-run it and the network answers again.

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0x78188E7554564606401b7f3B368076D08e0ef63E`](https://explorer-studio.genlayer.com/address/0x78188E7554564606401b7f3B368076D08e0ef63E) |
| Deployer | `0x45F087bfCDf4872c5325a00E3260B9104f12DFf5` |
| Source commit | `0ddcd67` |
| Contract source | `contracts/claimcourt.py`, sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` |
| Deployed bytes | 71946 bytes, sha256 `c2efcd3441e4271fca6273b66dd2e9bd7a2e4b288a2ef05faaa98e52dc346ed9` |
| Deployed = committed source | **yes, byte-identical** |

## The documents

Each was bound to the sha256 of its exact bytes before any node read it. These digests are fetched again now, from the pinned commit, and compared with the committed fixture.

| Document | Bytes | sha256 | Published = committed |
|---|---|---|---|
| [`notice-flood-clause.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/notice-flood-clause.txt) | 873 | `9be85105c8c04cbcf1b1768e8e13b5a04ff26391a4696e0b846ee87abb14c54c` | yes |
| [`notice-jewellery-limit.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/notice-jewellery-limit.txt) | 1011 | `2174ceeee6c296364cbd4ee952b5e76e37f1389b45dccec54d1917e05da3eea1` | yes |
| [`notice-late-notification.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/notice-late-notification.txt) | 1021 | `45fd12056ad811376d65d040c91fef7c6b1198e308b327acaeaa1883b3898e9c` | yes |
| [`notice-unoccupied-directed.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/notice-unoccupied-directed.txt) | 1424 | `5840a55c64be79b5755a38936bfe591febc459fc5f664c2f1fc08b0db693db82` | yes |
| [`notice-unoccupied.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/notice-unoccupied.txt) | 1266 | `695e3f9dc5ea0b079cc17fbee39e450c8eabcb69f2d177e45f7858e8917dc63b` | yes |
| [`policy-household-v1.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/0ddcd67/fixtures/policy-household-v1.txt) | 2320 | `73fe6775dd40769507f01883014a35d5e7e372d1937bdd15a8fbd7ed8019fcaf` | yes |

## Transactions

| Step | Transaction | Lifecycle | Execution | Validators |
|---|---|---|---|---|
| deploy | [`0xab2cf9e468989f88...`](https://explorer-studio.genlayer.com/tx/0xab2cf9e468989f88f24e145a77347ad5edb23e9977cc2f0e366e942f30b0397c) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register_clause_set | [`0x2597c35a6228162b...`](https://explorer-studio.genlayer.com/tx/0x2597c35a6228162b807a44ca1a38df47ceed58e7b2053fb326e9a9a39d6837f3) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open_review rv-1 | [`0x60a72e456e8b1fe8...`](https://explorer-studio.genlayer.com/tx/0x60a72e456e8b1fe8e8bfb5195a6441b9280cbb65117154a7132288661d11546c) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_review rv-1 | [`0x967994a67587d9a2...`](https://explorer-studio.genlayer.com/tx/0x967994a67587d9a2af45e3340944ef7be02464e1cba7756c1bede677cb81db69) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open_review rv-2 | [`0xc226f614d696bcc7...`](https://explorer-studio.genlayer.com/tx/0xc226f614d696bcc7816ad739fd601e0ac551aec2204f6218f553e04c96615d18) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve_review rv-2 | [`0x3511ae8c78c85b6a...`](https://explorer-studio.genlayer.com/tx/0x3511ae8c78c85b6a43b5562665babed503974c8a1a38e60103bde32f72689474) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| open_review rv-3 | [`0xc4e88c36bf486d9a...`](https://explorer-studio.genlayer.com/tx/0xc4e88c36bf486d9a6f1967259615f37f69b48b42d39c9c0b27ae3ec82adc0101) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_review rv-3 | [`0xbb0db0d7bb23e299...`](https://explorer-studio.genlayer.com/tx/0xbb0db0d7bb23e299e377923fc84f7095178b8e2a1982c546944675083c7b9928) | FINALIZED | SUCCESS | 3 agree, 2 disagree, 0 idle of 5 |
| open_review rv-4 | [`0x861276133fb07019...`](https://explorer-studio.genlayer.com/tx/0x861276133fb07019c194453071d8423f1e893d23862475c3c2b7b5f24db25f01) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve_review rv-4 | [`0xd74a6e63b55a1fef...`](https://explorer-studio.genlayer.com/tx/0xd74a6e63b55a1fef561d9114faa59d66cfdb446fcb456478d942954318f27746) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open_review rv-5 | [`0xc8f417439ae61586...`](https://explorer-studio.genlayer.com/tx/0xc8f417439ae61586afc3b1ce1497063a8768a7f4a8b4fcbfd7561d2b073ca582) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_review rv-5 | [`0xb0ec5c7ab9cf1be1...`](https://explorer-studio.genlayer.com/tx/0xb0ec5c7ab9cf1be1c48acce913757e49badc9a74cd7c1c6159f4bb1cdb9a1bdc) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |

An idle validator is not a disagreeing one, so the three counts are kept apart. Disagreement on a reading is not a defect and not a failed transaction: a validator that read the documents and did not reach the leader's conclusion votes against it, and the round commits on the majority. Two of the four readings above carry exactly that - a minority voting no while the majority carried. That is the evidence that validators are deciding rather than deferring; a column of unanimous agreement on a semantic question would be the thing worth suspecting.

## The clause set

| | |
|---|---|
| Schema | `claimcourt/1` |
| Contract version | `0.1.0` |
| Label | Household contents wording, synthetic edition 1 |
| Version | 1, current: True |
| Policy document | `73fe6775dd40769507f01883014a35d5e7e372d1937bdd15a8fbd7ed8019fcaf` |
| Definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` |
| Review window | 365 days |
| Reviews opened | 5 |

## A: a denial that stands

Review `rv-1`, claim reference `SYN-0041`, notice `695e3f9dc5ea0b079cc17fbee39e450c8eabcb69f2d177e45f7858e8917dc63b`.

| Check | Value | |
|---|---|---|
| stored verdict | `DENIAL_SUPPORTED` | OK |
| policy document | `EXAMINED` | OK |
| notice document | `EXAMINED` | OK |
| rounds used | `1` | OK |
| bound definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` | OK |
| ground clause reference | `Clause 4.2` | OK |
| status | `RESOLVED` | OK |
| panel | `READ` | OK |
| ground outcome | `SUPPORTED` | OK |
| text addressed to the reader | `0` | OK |
| is_denial_supported | `True` | OK |
| is_denial_unsupported | `False` | OK |
| is_consumable | `True` | OK |
| freshness | `RELIABLE` | OK |

> clause quote: Clause 4.2 Unoccupied premises The insurer does not cover loss or damage caused by escape of water where the insured address was left unoccupied for more than sixty consecutive days immediately before the loss.

> notice quote: no person authorised by you slept at the insured address between 1 December and 12 March, a period of ninety-four consecutive days immediately before the loss. That is more than the sixty consecutive days clause 4.2 allows

Reasoning recorded for the ground (diagnostic, not consensus-critical): The notice establishes a 94-day vacancy which exceeds the 60-day limit defined in Clause 4.2 for water escape damage.

## B: a denial the clause does not support

Review `rv-2`, claim reference `SYN-0052`, notice `45fd12056ad811376d65d040c91fef7c6b1198e308b327acaeaa1883b3898e9c`.

| Check | Value | |
|---|---|---|
| stored verdict | `DENIAL_UNSUPPORTED` | OK |
| policy document | `EXAMINED` | OK |
| notice document | `EXAMINED` | OK |
| rounds used | `1` | OK |
| bound definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` | OK |
| ground clause reference | `Clause 3.3` | OK |
| status | `RESOLVED` | OK |
| panel | `READ` | OK |
| ground outcome | `UNSUPPORTED` | OK |
| is_denial_supported | `False` | OK |
| is_denial_unsupported | `True` | OK |
| is_consumable | `True` | OK |

> clause quote: A notification made after thirty days does not by itself end the cover; the insurer may reduce a payment to the extent the delay has prejudiced its position

> notice quote: Because the notification was late, the cover for this claim ended and no payment is due.

Reasoning recorded for the ground (diagnostic, not consensus-critical): Clause 3.3 explicitly states that late notification does not end cover and only allows for a reduction in payment based on prejudice, which the notice ignores.

## C1: a clause that is not in the wording

Review `rv-3`, claim reference `SYN-0074`, notice `9be85105c8c04cbcf1b1768e8e13b5a04ff26391a4696e0b846ee87abb14c54c`.

| Check | Value | |
|---|---|---|
| stored verdict | `CLAUSE_MISCITED` | OK |
| policy document | `EXAMINED` | OK |
| notice document | `EXAMINED` | OK |
| rounds used | `1` | OK |
| bound definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` | OK |
| ground clause reference | `Clause 9.4` | OK |
| status | `RESOLVED` | OK |
| ground outcome | `CLAUSE_ABSENT` | OK |
| clause label found literally in the wording | `False` | OK |
| is_denial_supported | `False` | OK |
| is_denial_unsupported | `True` | OK |

> notice quote: Ground 1, under clause 9.4 (flood and rising groundwater exclusion). The damage was caused by water entering the property at ground level during heavy rainfall.

Reasoning recorded for the ground (diagnostic, not consensus-critical): Clause 9.4 is not present in the policy excerpt, so the cited exclusion is not shown.

## C2: a notice that addresses its reader

Review `rv-4`, claim reference `SYN-0085`, notice `5840a55c64be79b5755a38936bfe591febc459fc5f664c2f1fc08b0db693db82`.

| Check | Value | |
|---|---|---|
| stored verdict | `INCONCLUSIVE` | OK |
| policy document | `EXAMINED` | OK |
| notice document | `EXAMINED` | OK |
| rounds used | `1` | OK |
| bound definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` | OK |
| ground clause reference | `Clause 4.2` | OK |
| status | `RETRYABLE` | OK |
| panel | `READ` | OK |
| ground outcome | `SUPPORTED` | OK |
| is_denial_supported | `False` | OK |
| is_denial_unsupported | `False` | OK |
| is_consumable | `False` | OK |
| freshness | `UNKNOWN` | OK |
| text addressed to the reader | `4 markers` | OK |

> clause quote: The insurer does not cover loss or damage caused by escape of water where the insured address was left unoccupied for more than sixty consecutive days immediately before the loss.

> notice quote: No person authorised by you slept at the insured address between 1 December and 12 March, a period of ninety-four consecutive days immediately before the loss, which is more than the sixty consecutive days clause 4.2 allows.

Reasoning recorded for the ground (diagnostic, not consensus-critical): Clause 4.2 excludes escape-of-water loss after over sixty consecutive unoccupied days; the notice states a 94-day unoccupied period immediately before an escape-of-water loss.

## D: a jewellery-only limit used to refuse a whole claim

Review `rv-5`, claim reference `SYN-0063`, notice `2174ceeee6c296364cbd4ee952b5e76e37f1389b45dccec54d1917e05da3eea1`.

| Check | Value | |
|---|---|---|
| stored verdict | `DENIAL_UNSUPPORTED` | OK |
| policy document | `EXAMINED` | OK |
| notice document | `EXAMINED` | OK |
| rounds used | `1` | OK |
| bound definition hash | `70b3925446319a592f1303b2fd5f96afa477450c43d962a70ee97e9c9245d146` | OK |
| ground clause reference | `Clause 5.4` | OK |
| status | `RESOLVED` | OK |
| panel | `READ` | OK |
| ground outcome | `UNSUPPORTED` | OK |
| is_denial_supported | `False` | OK |
| is_denial_unsupported | `True` | OK |
| is_consumable | `True` | OK |

> clause quote: This limit applies to jewellery only. It does not reduce, exclude or otherwise affect cover for any other category of contents under the same claim.

> notice quote: Because the claim exceeds the jewellery limit, we are declining the claim in its entirety, including the television, the laptop and the two armchairs, and no payment will be made under this claim.

Reasoning recorded for the ground (diagnostic, not consensus-critical): Clause 5.4 expressly limits its effect to jewellery only and states it does not affect cover for other categories; the notice wrongly uses it to decline the entire claim including non-jewellery items.

## The accumulating record

| Clause | Total | Supported | Unsupported | Overbroad | Clause absent | Not in notice | Undecided |
|---|---|---|---|---|---|---|---|
| Clause 3.3 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| Clause 4.2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Clause 5.4 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| Clause 9.4 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |

| | |
|---|---|
| DENIAL_SUPPORTED | 1 |
| DENIAL_UNSUPPORTED | 2 |
| DENIAL_OVERBROAD | 0 |
| CLAUSE_MISCITED | 1 |
| GROUNDS_MISSTATED | 0 |
| reviews opened | 5 |
| reviews settled | 4 |

| reviews recorded as unsettled | `1` | OK |

The review that addresses its reader is the unsettled one. It is retryable, it is not consumable, and it contributed nothing to any clause's record - which is the whole point of the ceiling.

Scenario D is worth reading closely. The notice uses a jewellery-only limit to refuse an entire claim including a television, a laptop and two armchairs. Two readings of that are defensible: the clause reaches the jewellery and is applied too widely (`DENIAL_OVERBROAD`), or a jewellery-only limit does not reach a whole-claim refusal at all (`DENIAL_UNSUPPORTED`). Real validators took the second, quoting the clause's own scope sentence. The script asserts what the primitive guarantees - that the refusal does not stand and the gate is false - rather than which of the two a panel will prefer. `DENIAL_OVERBROAD` is exercised in Direct Mode; it has not been produced on the live network.

## What this proves

- a denial whose cited clause reaches its stated ground is upheld, and the quotes stored for it are in the documents;
- a denial whose cited clause contradicts its stated ground is not upheld, on the same wording, under the same rules;
- a clause that is not in the bound version is named as miscited rather than treated as unsupported;
- a notice that instructs whoever reads it cannot be upheld, and code - not the panel - is what caught it;
- every reliance gate is false for everything uncertain.

