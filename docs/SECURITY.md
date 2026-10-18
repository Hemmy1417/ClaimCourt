# Security

## What is being protected

| Asset | Why it matters |
|---|---|
| the stored verdict | downstream systems gate on it; a false `COVERAGE_SUPPORTED` pays a claim that should not be paid, a false `COVERAGE_NOT_ESTABLISHED` refuses one that should |
| the binding between a claim and a policy version | a verdict means nothing if the wording, the conditions or the exclusions it was judged under can be changed afterwards |
| the binding between a claim and its documents | an adjudication of bytes nobody can re-fetch proves nothing |
| the stored quotes | they are the evidence that the reading came from the documents; an invented quote is a forged finding |
| the fraud finding | the one output that accuses a person, and the one most dangerous to get wrong |
| the per-policy record | counters that must not be inflatable by replay or retry |

No funds are held. Nothing is payable. There is no token.

## Actors and what each is assumed to be capable of

| Actor | Assumed capability |
|---|---|
| policy owner (insurer or scheme) | publishes and revokes versions, opens and cancels challenges; may try to change the terms under a claim already submitted, or to set conditions nobody can meet |
| claimant | chooses which documents to commit and what to say about the incident; may supply documents written to influence whoever reads them, or reuse a document from another claim |
| any caller | may resolve or retry any submission; may try to replay a settled one |
| the document hosts | may serve different bytes later, go offline, or rate-limit |
| the documents themselves | hostile input: they are authored by an interested party |
| the leader validator | may return a well-formed, confident, substantively false adjudication, or fail on purpose |
| a validator minority | may vote dishonestly |
| downstream consumer | may read any view at any time, including mid-lifecycle |

## Trust assumptions

- GenLayer's own honest-majority assumption for the round.
- The sha256 of a document is a sound commitment to its bytes.
- A validator's runtime can fetch an `https` location, and its egress policy
  is the real boundary on what it will fetch.
- Whoever registers a policy is entitled to say what that policy is. The
  contract cannot verify that a published wording is the one a claimant
  actually bought.
- Validators read the languages the documents are written in.

## Input attacks and what stops each

| Attack | Defence |
|---|---|
| change the wording or the conditions under a submitted claim | a version is immutable; a new version gets its own number and policy hash, and existing claims keep theirs |
| swap a document's bytes after submission | every document is bound by sha256; a mismatch is `HASH_MISMATCH` and the bytes are never read |
| submit a claim without the evidence the policy needs | the required kinds are checked at submission, and again at adjudication against what is actually readable |
| submit after the deadline | the claim deadline is compared with the transaction clock at submission |
| point a claim at a local or internal address | `_admit_url` refuses non-`https`, embedded credentials, explicit ports, `localhost`, `.localhost`, `.local`, `.internal`, loopback, private, link-local and multicast IPv4, raw IPs, malformed hosts, hosts with no dot, and anything outside printable ASCII |
| commit a document large enough to exhaust the round | a 200,000-byte cap, checked after the hash and before any decode |
| write the evidence at the adjudicator | markers are counted in code, validators must agree on the count, and evidence carrying them cannot reach `COVERAGE_SUPPORTED` |
| make the panel invent support for a condition | every substantive finding must quote the document it names, and each validator re-checks the quote against its own bytes |
| make the panel invent an exclusion, a contradiction or an accusation | the same rule, applied to each; an ungrounded one is downgraded to `UNCLEAR`, never to its opposite |
| persuade the panel that a parametric trigger fired | the panel reads the number and quotes it; code compares it with the threshold, and the prompt says in terms not to decide the comparison |
| accuse a claimant where the policy asked nothing | an unsolicited fraud answer makes the whole response unusable |
| report an outcome the findings do not support | the gate re-derives the verdict and the criteria and refuses a payload whose outcome does not follow |
| hand back a wrongly typed or unknown value | strict readers: exact booleans, exact integers, known enums, bounded strings, one row per condition in the policy's order |
| settle a claim twice, or retry a settled one | status transitions are checked; counters move once, guarded by a `counted` flag |
| retry forever | three rounds, after which the claim resolves with its unsettled verdict and is never consumable |
| keep a verdict alive after withdrawing the policy version | revoking a version makes its claims `BLOCKED` and not consumable, without rewriting their verdicts |
| rely on an ancient adjudication | freshness is explicit per policy version, and `is_consumable` is false past the window |
| grow the state without bound | caps on conditions, exclusions, evidence documents, required kinds, rounds, versions, challenges, submissions, URL and text lengths, quote length, document size and page size |

## Fail-closed policy

Every default is the cautious one:

- a document that cannot be examined is `EVIDENCE_UNAVAILABLE`, never a
  finding either way;
- a panel that did not answer usably is `INCONCLUSIVE`;
- a condition that cannot be settled is `INCONCLUSIVE` for the whole claim;
- an ungrounded finding is downgraded to `UNCLEAR` - never to its opposite;
- an unknown enum value, a wrong type or a missing field is a failure, not a
  default;
- a measurement that cannot be grounded is no measurement, so a trigger
  cannot fire on it;
- evidence that addresses its reader cannot win coverage;
- `is_coverage_supported` is false unless the claim is settled, on a live
  policy version, inside its freshness window.

## Fraud, specifically

`FRAUD_INDICATORS_FOUND` is the only verdict that says something about a
person rather than about a claim, so it is the most constrained thing in the
contract:

- it exists only where the policy declares a bounded fraud question;
- the panel is told in terms that missing or incomplete evidence is never an
  indicator;
- the answer must quote the document it rests on, and each validator
  re-checks that quote against its own bytes;
- an ungrounded accusation becomes `UNCLEAR`, which is itself
  `INCONCLUSIVE` - not an acquittal, and not a finding;
- validators must agree on the fraud finding exactly;
- and a finding of indicators is still only that: indicators, in these
  documents, under this policy's own question. It is not a determination of
  fraud, and nothing in this contract treats it as one.

## Privacy

What is stored on chain: the policy's location and digest, its conditions
and exclusions as the owner published them, each document's location,
digest, kind and status, a short claimant reference, a bounded incident
summary, an incident date, a location reference, a loss category, an amount
**band**, the grounded quotes, one sentence of reasoning per finding, the
findings, the verdict and the counters.

What must never be put here: identity documents, medical records, bank
statements, loss adjuster files, claimant names or addresses. The claimant
reference is meant to be an opaque or synthetic handle, and the amount is a
band rather than a figure. Every document a claim commits becomes public by
construction, because a validator has to fetch it: anything that cannot be
published should not be the basis of a claim here.

Every fixture in this repository is synthetic and labelled `TEST /
DEMONSTRATION ONLY` and `NOT FOR PRODUCTION`. No real policy, claim,
insurer or person appears anywhere in it.

## Payout boundary

This contract adjudicates. It does not pay, and it has no payable method,
no token, no bond and no balance. A verdict is a machine-readable
adjudication result. Any payout system built on it must separately enforce
its own authorisation, its own limits, its own finality rules and its own
insurer-side checks - and must not treat `COVERAGE_SUPPORTED` as an
instruction to pay.

## Limitations

- Not legal advice, not a regulatory determination, not a replacement for a
  licensed adjuster, and not a substitute for an insurer's own claims
  process.
- `COVERAGE_SUPPORTED` means the conditions were met on the documents
  reviewed under that policy version. It does not guarantee payment and does
  not bind anyone.
- `COVERAGE_NOT_ESTABLISHED` means the evidence reviewed did not establish a
  condition. It is not a finding that the claim is false, and it is never a
  finding of fraud.
- The contract cannot tell whether a published wording is the policy a
  claimant actually holds, only that it is the one the claim was bound to.
- The URL rules are defence in depth, not SSRF prevention; a validator
  runtime's egress policy matters as much.
- Prompt-injection handling is layered - data framing, marker counting,
  quote grounding, a verdict ceiling - and layered is not immune.
- Honest validators may label an individual condition differently; only the
  outcome is consensus-critical, by design, and the reasoning is why that is
  safe.
- A genuinely close claim may land on `INCONCLUSIVE`. That is the intended
  behaviour, not a failure.
- Studionet deployment for demonstration and reuse, not an audited
  production system.

## Reporting

Open an issue on the repository. There is no bounty, nothing is payable, and
no production system depends on this deployment.
