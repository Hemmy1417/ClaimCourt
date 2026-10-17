# Security

## What is being protected

| Asset | Why it matters |
|---|---|
| the stored verdict | downstream contracts gate on it; a false `DENIAL_SUPPORTED` lets a bad refusal stand, a false `DENIAL_UNSUPPORTED` brands a sound one |
| the binding between a review and a clause version | a verdict means nothing if the wording it was read against can be changed afterwards |
| the stored quotes | they are the evidence that the reading came from the documents; an invented quote is a forged record |
| the per-clause record | a conduct signal; it must not be inflatable by replaying or retrying a review |
| the ability to open a review | if the reviewed party could block or own reviews, the primitive would be decorative |

No funds are held. Nothing is payable. There is no token.

## Actors and what each is assumed to be capable of

| Actor | Assumed capability |
|---|---|
| clause set owner (the decider, or whoever publishes the wording) | may publish and revoke versions; may try to change the wording under a past verdict; may write a notice that addresses whoever reads it |
| review opener (a claimant, a platform, anyone) | may choose which notice to review and how to phrase the grounds; may try to frame grounds the notice never gave |
| any caller | may resolve or retry any review; may try to replay a settled one |
| the document hosts | may serve different bytes later, go offline, or rate-limit |
| the notice itself | hostile text: it is written by the party under review |
| the leader validator | may return a well-formed, confident, substantively false payload, or fail on purpose |
| a validator minority | may vote dishonestly |
| downstream consumer | may read any view at any time, including mid-lifecycle |

## Trust assumptions

- GenLayer's own honest-majority assumption for the round.
- The sha256 of a document is a sound commitment to its bytes.
- A validator's runtime can fetch an `https` location, and its egress
  policy is the real boundary on what it will fetch.
- Whoever registers a clause set is entitled to say what wording that
  clause set is. The contract does not and cannot verify that a published
  document is the policy a real claimant bought.
- Validators read the same languages the documents are written in.

## Input attacks and what stops each

| Attack | Defence |
|---|---|
| swap the policy or notice bytes after a review is opened | both are bound by sha256 at admission; a mismatch is `HASH_MISMATCH`, never a finding |
| point a review at a local or internal address | `_admit_url` refuses non-`https`, embedded credentials, explicit ports, `localhost`, `.localhost`, `.local`, `.internal`, loopback, private, link-local and multicast IPv4, raw IPs, malformed hosts, hosts with no dot, and anything outside printable ASCII |
| feed in a document large enough to exhaust the round | 200,000-byte cap, checked after the hash and before any decode |
| instruct the reader from inside the notice | the markers are counted in code, validators must agree on the count, and a notice carrying any of them cannot reach `DENIAL_SUPPORTED` |
| bury the decisive clause past a truncation point | the panel sees a deterministic window of the policy around each cited label, not the head of the document |
| make the panel invent a clause | every positive answer must quote the document, and the quote is re-checked against each node's own verified bytes |
| frame grounds the notice never stated | the panel must find the ground in the notice and quote it; otherwise the verdict is `GROUNDS_MISSTATED`, which names the opener's error rather than the decider's |
| hand back a wrongly typed or unknown value | strict readers: exact booleans, exact integers, known enums, bounded strings, one row per ground, no duplicate index |
| sneak a positive through an unparseable answer | an unusable answer is `INVALID`, which derives `INCONCLUSIVE`; unknown verdict words never map onto known ones |
| settle a review twice, or retry a settled one | status transitions are checked against `OPEN` and `RETRYABLE`; counters move once, guarded by a `counted` flag |
| review the same notice twice to double its weight in the record | the notice digest is registered to one review; it is released only when that review is withdrawn before settlement |
| retry forever | three rounds, after which the review resolves with its unsettled verdict and is never consumable |
| change the wording under a past verdict | a version is immutable; a new version gets a new number and definition hash, and old reviews keep theirs |
| keep a verdict alive after withdrawing the rule | revoking a version makes its reviews `BLOCKED` and not consumable, without rewriting their verdicts |
| rely on an ancient verdict | freshness is explicit per clause set, and `is_consumable` is false past the window |
| grow the state without bound | caps on grounds, rounds, versions, reviews per version, URL length, text lengths, quote length, document size and page size |

## Fail-closed policy

Every default is the cautious one:

- a document that cannot be examined is `RECORD_UNAVAILABLE`, never a
  finding either way;
- a panel that did not answer usably is `INCONCLUSIVE`;
- a ground that cannot be settled is `INCONCLUSIVE` for the whole review;
- an ungrounded "located" is not located; an ungrounded "stated" is not
  stated;
- an unknown enum value, a wrong type or a missing field is a failure, not
  a default;
- a notice that addresses its reader cannot be upheld;
- `is_consumable`, `is_denial_supported` and `is_denial_unsupported` are
  all false unless the review is settled, on a live version, inside its
  freshness window;
- `DENIAL_OVERBROAD` makes both of the convenience booleans false: it is
  neither a clean upholding nor a plain lack of support, and a consumer
  that cares must read the verdict.

## Privacy

What is stored on chain: the two document locations and digests, a short
claim reference the opener chooses, the cited clause labels, the grounds as
the opener states them, the quotes the panel grounded, one sentence of
reasoning per ground, the outcome, and the counters.

What is not stored, and must not be: identity documents, medical records,
bank details, loss adjuster files, claimant names or addresses. The claim
reference is intended to be an opaque or synthetic handle. The demonstration
fixtures are synthetic and labelled; nothing in this repository is a real
policy, a real notice or a real person's claim.

Both documents are public by construction - a validator has to be able to
fetch them. Anything that cannot be published should not be the basis of a
review here.

## Limitations

This is not a guarantee of anything, and in particular:

- it is not legal advice, a regulatory determination, or an ombudsman
  decision, and a verdict does not oblige anyone to pay anything;
- `DENIAL_UNSUPPORTED` means the stated reason did not stand up on the two
  documents reviewed. It does not mean the claim is valid, that the loss
  happened, or that a different reason would not stand;
- `DENIAL_SUPPORTED` means the stated reasons stood up as written. It does
  not mean the decision was fair, proportionate, or lawful;
- the contract cannot tell whether the published wording is the wording a
  claimant actually bought, only that it is the wording the review was
  bound to;
- the URL rules are defence in depth, not SSRF prevention; the validator
  runtime's egress policy matters as much;
- prompt-injection handling is layered - data framing, marker counting,
  quote grounding, a verdict ceiling - and layered is not immune;
- honest validators may phrase reasoning differently; only the
  decision-critical fields are consensus-critical, by design;
- semantic reading of a legal provision is genuinely hard, and a close
  question may land on `INCONCLUSIVE`, which is the intended behaviour
  rather than a failure;
- this is a Studionet deployment for demonstration and reuse, not an
  audited production system.

## Reporting

Open an issue on the repository. There is no bounty, nothing is payable,
and no production system depends on this deployment.
