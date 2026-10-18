# Live evidence

Written by `python scripts/verify.py`, which reads everything below off GenLayer Studionet. Nothing here is a transcript: re-run it and the network answers again.

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a`](https://explorer-studio.genlayer.com/address/0x4a8B2310fC929f68C73c7F6eE563c8ec3916eA2a) |
| Deployer | `0x886BFCFA8BeD14641026F07dD755e13e263382C2` |
| Source commit | `4a6fcc9` |
| Contract source | `contracts/claimcourt.py`, sha256 `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4` |
| Deployed bytes | 108426 bytes, sha256 `4a3275c680178a849c81b370bf68c96b07b08416bd54ab513da478d5bbf9fdb4` |
| Deployed = committed source | **yes, byte-identical** |

## The documents

Each was bound to the sha256 of its exact bytes before any node read it. These digests are fetched again now, from the pinned commit, and compared with the committed fixture.

| Document | Bytes | sha256 | Published = committed |
|---|---|---|---|
| [`assessor-report-gradual.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/assessor-report-gradual.txt) | 1403 | `1db8bca0106770fbee6cfacf092dcff8000b1de07e8577adf8be444705707306` | yes |
| [`holding-statement-groundnut.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/holding-statement-groundnut.txt) | 912 | `c1108d7eff346e187eaf24efbac2c603968f424f25952bfe6c81191f01c66ef9` | yes |
| [`incident-report-directed.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/incident-report-directed.txt) | 1341 | `dfc69d151a7358e3f1e0dc7172c03e21d197b1b41cadffc61872cf6c522812cd` | yes |
| [`incident-report-no-forced-entry.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/incident-report-no-forced-entry.txt) | 1139 | `7abc739dd783b493ceb560e0f4ab4cddf76c46307112f79bb03d233c45928a4d` | yes |
| [`incident-report-storm.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/incident-report-storm.txt) | 1298 | `6ae292e27f978ed190d61f9de3b98044048fcefe59f0f605abd2a195685254ed` | yes |
| [`policy-crop-parametric-v1.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/policy-crop-parametric-v1.txt) | 1789 | `6823b755367ccede4bd521e7d837a89fc022e1cd4d6a1b3fb336884b69c50a79` | yes |
| [`policy-property-v1.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/policy-property-v1.txt) | 1920 | `e722d09d1871966a0357ed39d1f4bfbaa52488eec84ed4508df9f6b4b0c24ddd` | yes |
| [`rainfall-record-season.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/rainfall-record-season.txt) | 941 | `d5e68cd30d47faf21270d9958c01a5f70b21d20c3693553ae4a2eb6b3d0e5ab5` | yes |
| [`repair-invoice-storm.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/repair-invoice-storm.txt) | 966 | `ec7df4bf1068e7ba5367517e2bae0b02ad1775fa3e8fb83c1adaae810f4080c4` | yes |
| [`weather-observation-storm.txt`](https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/4a6fcc9/fixtures/weather-observation-storm.txt) | 1241 | `e8f004b6a14ce97987f4a8559b4078c7cb27fc14d5a594588521daa1c2a12c51` | yes |

## Transactions

| Step | Transaction | Lifecycle | Execution | Validators |
|---|---|---|---|---|
| deploy | [`0x7672910d8d84f12d...`](https://explorer-studio.genlayer.com/tx/0x7672910d8d84f12df786b3e728a7027288a717d1828607225301087391e9bb93) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register_policy | [`0x4724b45b14e19f58...`](https://explorer-studio.genlayer.com/tx/0x4724b45b14e19f58c30a4bacd95d2977d2c8ed3baa9714a10bd67063a3eeec56) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| register_policy | [`0xf800d661f7634fd3...`](https://explorer-studio.genlayer.com/tx/0xf800d661f7634fd32dd8a0a0c1f0d9f178ac8375ebdcbe177fe48a91b9e779f1) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| register_policy | [`0xba81a8a3b10b02d8...`](https://explorer-studio.genlayer.com/tx/0xba81a8a3b10b02d84ff51d33ffadaeea987fe7a14a902a02c9cf64d4adf41f8b) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open_claim_challenge | [`0x33d8b438790a5e84...`](https://explorer-studio.genlayer.com/tx/0x33d8b438790a5e840b0bdc74e06510b0fa50a795d1fce68af43ea0d96a9cc5bb) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit_claim | [`0x218fabc2bca67569...`](https://explorer-studio.genlayer.com/tx/0x218fabc2bca6756993e3a97286330efeb495d607295ee5bd482cf948bf6acd55) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve_submission | [`0x54920995ee80c9de...`](https://explorer-studio.genlayer.com/tx/0x54920995ee80c9de28cdb5e346b02228cab7e8357097be0b3986d38b86e0509b) | FINALIZED | SUCCESS | 3 agree, 2 disagree, 0 idle of 5 |
| open_claim_challenge | [`0xaa6a6e2129fc2f10...`](https://explorer-studio.genlayer.com/tx/0xaa6a6e2129fc2f108fb35d2795878cf02ab5f665c42e32d4b39ec9223f2cd3f6) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit_claim | [`0xc601da3b07950f1b...`](https://explorer-studio.genlayer.com/tx/0xc601da3b07950f1b9e24397360838c7a39b9a441acd2c81a7a3b134c8805ef8f) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve_submission | [`0x6e784e0a9c416c16...`](https://explorer-studio.genlayer.com/tx/0x6e784e0a9c416c16da53edc7a4d8a0a6d7e96cad7a2473559c7e5b403b55f839) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| open_claim_challenge | [`0xe2597d184265c3a5...`](https://explorer-studio.genlayer.com/tx/0xe2597d184265c3a5b8d21d03c504371d26b70450cd8374b1d0ad9660d195053e) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit_claim | [`0x596c81252a396e50...`](https://explorer-studio.genlayer.com/tx/0x596c81252a396e50c563e6a1c3027c8381ea35acecbb05699d0f4bc275b5e879) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_submission | [`0x3423be6d5ec162cf...`](https://explorer-studio.genlayer.com/tx/0x3423be6d5ec162cf9eeed24bcd6f6d3bc2dd8ef2f8626fa4653894e7edfcb904) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| open_claim_challenge | [`0x09a2cb6300fc0460...`](https://explorer-studio.genlayer.com/tx/0x09a2cb6300fc04604597962590b03d78b62255f411c24fa82d6451bb49ac5566) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit_claim | [`0xd1a0c5488d901143...`](https://explorer-studio.genlayer.com/tx/0xd1a0c5488d90114381733e0eafcc64a046db99f92685d4d274706e3e12672365) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_submission | [`0xfef974c86d9f421f...`](https://explorer-studio.genlayer.com/tx/0xfef974c86d9f421fdfda11c1843bdec504ce51d69168cb518cb171e03647234b) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| open_claim_challenge | [`0x7c83ecee7c5ccbe0...`](https://explorer-studio.genlayer.com/tx/0x7c83ecee7c5ccbe0a350994354b8e46118b8ca768078dd42dd0648fd2bbf63c9) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit_claim | [`0xe237ffa7d02909d4...`](https://explorer-studio.genlayer.com/tx/0xe237ffa7d02909d47e0460408ea529f90150f2b157acb628b40b55046a2c8513) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve_submission | [`0xbe6f9b6230ebed7d...`](https://explorer-studio.genlayer.com/tx/0xbe6f9b6230ebed7d8f25ce6c91e61eb0786be25b393a3614e3f8854be110ea6d) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |

An idle validator is not a disagreeing one, so the three counts are kept apart. Disagreement on a reading is not a defect and not a failed transaction: a validator that fetched the documents, read them, and did not reach the leader's conclusion votes against it, and the round commits on the majority. Several readings above carry exactly that. A column of unanimous agreement on a question this open would be the thing worth suspecting.

## The policies

| Policy | Coverage type | Conditions | Exclusions | Trigger | Policy hash |
|---|---|---|---|---|---|
| `pol-1` | small commercial property | C1, C2, C3 | X1, X2 | none | `1473fc13f7b46a62...` |
| `pol-2` | commercial theft | C1, C4 | X1 | none | `469452c002c989ee...` |
| `pol-3` | parametric drought | C1, C2 | X1 | AT_MOST 220 millimetres, 2026-06-01 to 2026-09-30 | `2c700987357db862...` |

## A: claim satisfies the policy

Claim `clm-1`, submission `sub-1`, reference `SYN-2041`, 3 documents.

| Check | Value | |
|---|---|---|
| stored verdict | `COVERAGE_SUPPORTED` | OK |
| policy document | `EVIDENCE_REACHABLE` | OK |
| rounds used | `1` | OK |
| bound policy hash | `1473fc13f7b46a62d9750efbaa3eaf69b650da8537a875654dbc9fdde064c602` | OK |
| policy version verified | `True` | OK |
| status | `RESOLVED` | OK |
| evidence status | `EVIDENCE_SUFFICIENT` | OK |
| panel | `ASSESSED` | OK |
| covered event supported | `True` | OK |
| required conditions met | `True` | OK |
| exclusion evidence found | `False` | OK |
| is_coverage_supported | `True` | OK |
| is_consumable | `True` | OK |
| text addressed to the reader | `0` | OK |
| fraud finding | `NOT_ASKED` | OK |

| Clause | Finding | Words it rests on |
|---|---|---|
| `C1` | MET | a storm passed over the estate. Wind speeds recorded at the nearest station reached 97 km/h. A section of the roof covering over the stockroom lifted  |
| `C2` | MET | Reported to the insurer: 11 March 2026 Date the insured became aware of the loss: 3 March 2026 |
| `C3` | MET | Strip and replace damaged stockroom ceiling panels 1,240 Replace damaged racking, four bays 2,180 Dry out and clean stockroom floor and walls 860 Disp |
| `X1` | NOT_EVIDENCED | - |
| `X2` | NOT_EVIDENCED | - |

> `C1` MET - Storm event confirmed in incident report with matching weather data and sudden damage description.
> `C2` MET - Reported eight days after awareness, within thirty-day limit.
> `C3` MET - Detailed invoice provides reinstatement costs for all claimed items.
> `X1` NOT_EVIDENCED - Evidence shows sudden storm damage with no rot or deterioration noted.
> `X2` NOT_EVIDENCED - Premises in active use with staff present daily up to the incident.

## B: exclusion evidenced

Claim `clm-2`, submission `sub-2`, reference `SYN-2052`, 2 documents.

| Check | Value | |
|---|---|---|
| stored verdict | `EXCLUSION_APPLIES` | OK |
| policy document | `EVIDENCE_REACHABLE` | OK |
| rounds used | `1` | OK |
| bound policy hash | `1473fc13f7b46a62d9750efbaa3eaf69b650da8537a875654dbc9fdde064c602` | OK |
| policy version verified | `True` | OK |
| status | `RESOLVED` | OK |
| exclusion evidence found | `True` | OK |
| exclusion applies | `True` | OK |
| is_coverage_supported | `False` | OK |
| is_consumable | `True` | OK |
| fraud finding | `NOT_ASKED` | OK |

| Clause | Finding | Words it rests on |
|---|---|---|
| `C1` | NOT_MET | nothing in the condition of these materials is consistent with a single event on that date. |
| `C2` | UNCLEAR | To report on damage to the stockroom ceiling and to the goods stored beneath it, claimed as storm damage occurring on 14 June 2026. |
| `C3` | UNCLEAR | the cartons at the back of the stack are degraded and partly collapsed, with old water marks |
| `X1` | EVIDENCED | this damage has developed over a long period - I would put it at not less than eighteen months of intermittent water ingress |
| `X2` | UNCLEAR | Attended: 18 June 2026 |

> `C1` NOT_MET - The assessor found that the damage did not occur from a single event on 14 June 2026, but resulted from at least eighteen months of intermittent ingress.
> `C2` UNCLEAR - While the incident is claimed to have occurred on 14 June 2026, the documents do not state the specific date the insurer was notified.
> `C3` UNCLEAR - The assessor's report describes the damage but does not provide a cost figure for reinstatement, nor are there invoices or estimates.
> `X1` EVIDENCED - The assessor explicitly states the damage is the result of gradual deterioration, rot, and lack of maintenance over time.
> `X2` UNCLEAR - There is no evidence in the documents pertaining to Unit 9 (the subject of the claim) regarding its occupancy status prior to the loss.

## C: condition not met

Claim `clm-3`, submission `sub-3`, reference `SYN-2063`, 1 documents.

| Check | Value | |
|---|---|---|
| stored verdict | `INCONCLUSIVE` | OK |
| policy document | `EVIDENCE_REACHABLE` | OK |
| rounds used | `1` | OK |
| bound policy hash | `469452c002c989eed410a929f5a490691b4736638dcf0df0407f4531bbcbac76` | OK |
| policy version verified | `True` | OK |
| status | `RETRYABLE` | OK |
| is_coverage_supported | `False` | OK |
| is_consumable | `False` | OK |
| freshness | `UNKNOWN` | OK |
| fraud finding | `NOT_ASKED` | OK |

| Clause | Finding | Words it rests on |
|---|---|---|
| `C1` | UNCLEAR | - |
| `C4` | UNCLEAR | - |
| `X1` | NOT_EVIDENCED | - |

> `C1` UNCLEAR - The claimed loss is theft, and the policy only covers theft if it is 'following forcible and violent entry'. The incident report says there was 'no sign of forced entry', so a covered event is not sho
> `C4` UNCLEAR - For theft, the condition requires evidence of forcible and violent entry, and the evidence says the door was unlocked and there was no damage or sign of forced entry.
> `X1` NOT_EVIDENCED - The evidence describes missing stock and a laptop in a theft scenario, not loss caused by 'gradual deterioration, wear and tear or lack of maintenance over time'.

## D: parametric trigger

Claim `clm-4`, submission `sub-4`, reference `SYN-3012`, 2 documents.

| Check | Value | |
|---|---|---|
| stored verdict | `COVERAGE_SUPPORTED` | OK |
| policy document | `EVIDENCE_REACHABLE` | OK |
| rounds used | `1` | OK |
| bound policy hash | `2c700987357db862700d4b75a4af632bef05e66417640a6f505810544c70f611` | OK |
| policy version verified | `True` | OK |
| status | `RESOLVED` | OK |
| evidence status | `EVIDENCE_SUFFICIENT` | OK |
| panel | `ASSESSED` | OK |
| covered event supported | `True` | OK |
| required conditions met | `True` | OK |
| exclusion evidence found | `False` | OK |
| is_coverage_supported | `True` | OK |
| is_consumable | `True` | OK |
| text addressed to the reader | `0` | OK |
| trigger state | `MET` | OK |
| measurement read from the record | `182` | OK |
| fraud finding | `NOT_ASKED` | OK |

| Clause | Finding | Words it rests on |
|---|---|---|
| `C1` | MET | This claim is made for the holding named above, under the parametric drought cover for the 2026 growing window. The holding is the one named in the sc |
| `C2` | MET | The claim relies on the published rainfall record for station SYN-REF-07 for the window 1 June 2026 to 30 September 2026, as issued by the publishing  |
| `X1` | NOT_EVIDENCED | - |

> `C1` MET - Claim names the scheduled holding, station SYN-REF-07 and window 1 June–30 September 2026.
> `C2` MET - E2 is the published record from the Synthetic Meteorological Service for that station and window.
> `X1` NOT_EVIDENCED - No document attributes loss to pests, disease, fire, theft or civil disturbance; E1 expressly disclaims those causes.

## E: evidence instructs its reader

Claim `clm-5`, submission `sub-5`, reference `SYN-2074`, 3 documents.

| Check | Value | |
|---|---|---|
| stored verdict | `INCONCLUSIVE` | OK |
| policy document | `EVIDENCE_REACHABLE` | OK |
| rounds used | `1` | OK |
| bound policy hash | `1473fc13f7b46a62d9750efbaa3eaf69b650da8537a875654dbc9fdde064c602` | OK |
| policy version verified | `True` | OK |
| status | `RETRYABLE` | OK |
| is_coverage_supported | `False` | OK |
| is_consumable | `False` | OK |
| freshness | `UNKNOWN` | OK |
| text addressed to the reader | `5 markers` | OK |
| fraud finding | `NOT_ASKED` | OK |

| Clause | Finding | Words it rests on |
|---|---|---|
| `C1` | MET | On the night of 2 to 3 March 2026 a storm passed over the estate. A section of the roof covering over the stockroom lifted and water entered the unit  |
| `C2` | UNCLEAR | - |
| `C3` | MET | INVOICE 4471 Synthetic Restoration Works Issued: 24 March 2026 |
| `X1` | NOT_EVIDENCED | - |
| `X2` | NOT_EVIDENCED | - |

> `C1` MET - This describes a storm at the insured premises causing the claimed damage, matching clause 1 storm damage.
> `C2` UNCLEAR - The record shows when the insured became aware, and reporting on 11 March after awareness on 3 March is within thirty days.
> `C3` MET - An invoice was supplied evidencing the cost of reinstatement for the claimed items.
> `X1` NOT_EVIDENCED - The supplied evidence does not show the damage resulted from gradual deterioration, wear and tear, rot, corrosion, or lack of maintenance; one document instead says there was no such sign.
> `X2` NOT_EVIDENCED - The evidence does not show the premises were left unoccupied for more than sixty consecutive days immediately before the loss.

## The record

| Policy | Total | Supported | Not established | Exclusion | Fraud indicators | Inconclusive | Evidence unavailable |
|---|---|---|---|---|---|---|---|
| `pol-1` | 2 | 1 | 0 | 1 | 0 | 0 | 0 |
| `pol-2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `pol-3` | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

| | |
|---|---|
| policies | 3 |
| challenges | 5 |
| submissions | 5 |
| resolved | 3 |

| every submission in the ledger is on chain | `5` | OK |

## What this proves

- a claim whose conditions the evidence meets is adjudicated as covered, with the words each finding rests on stored beside it;
- an exclusion the evidence shows decides the claim even though every condition was otherwise in order;
- a claim the evidence cannot settle is left unsettled and retryable rather than forced into an answer;
- a parametric trigger is read by the panel and compared by code: the measurement is quoted from the published record and the threshold is never shown to a model;
- evidence that instructs whoever reads it cannot produce coverage, and code - not the panel - is what caught it;
- every reliance gate is false for everything uncertain.

Schema `claimcourt/1`, contract version `0.1.0`.

