#!/usr/bin/env python3
"""Mutation sweep: break one safety rule at a time and prove the suite
notices.

A green test suite says the contract passes its tests. It does not say the
tests would fail if the contract were wrong. Each mutation below removes
exactly one guard in a scratch copy of the contract; the Direct Mode suite
is then run against that copy. A mutation that still passes is a hole in
the tests, and is reported as SURVIVED.

    python scripts/mutate.py            # every mutation
    python scripts/mutate.py grounding  # only mutations matching a word

Run it with output straight to a file - `python -u scripts/mutate.py > log`
- because piping it through another process buffers the progress away.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "claimcourt.py"

# (label, find, replace) - `find` must occur exactly once in the source.
MUTATIONS = [
    ("grounding: any quote is accepted",
     '    return flat_quote in _flat(text)',
     '    return True'),
    ("grounding: a one-word quote counts",
     'QUOTE_MIN = 12',
     'QUOTE_MIN = 0'),
    ("grounding: an ungrounded finding keeps its force",
     '        if finding in [CONDITION_MET, CONDITION_NOT_MET] \\\n'
     '                and not held["grounded"]:\n'
     '            finding = CONDITION_UNCLEAR',
     '        pass'),
    ("grounding: an ungrounded accusation stands",
     '        if not held["grounded"]:\n'
     '            # An accusation without a quote is not an accusation.\n'
     '            fraud["finding"] = FRAUD_UNCLEAR',
     '        if False:\n'
     '            fraud["finding"] = FRAUD_UNCLEAR'),
    ("types: an integer passes for a boolean",
     'def _exact_bool(value):\n    if isinstance(value, bool):',
     'def _exact_bool(value):\n    if isinstance(value, int):'),
    ("types: an unknown condition finding is kept",
     '        if finding not in [CONDITION_MET, CONDITION_NOT_MET,\n'
     '                           CONDITION_UNCLEAR]:\n'
     '            return None',
     '        pass'),
    ("gate: a substantive finding needs no words",
     '        if row["finding"] in [CONDITION_MET, CONDITION_NOT_MET] \\\n'
     '                and row["quote"] == "":\n'
     '            return None',
     '        pass'),
    ("gate: an unassessed round may carry findings",
     '        if panel_state != PANEL_ASSESSED \\\n'
     '                and row["finding"] != CONDITION_NOT_ASSESSED:\n'
     '            return None',
     '        pass'),
    ("gate: the payload need not be bound to this submission",
     '    if payload.get("submission_id") != ctx["submission_id"]:\n'
     '        return None',
     '    pass'),
    ("gate: the panel state need not match the record",
     '    if panel_state == PANEL_SKIPPED and convenable:\n'
     '        return None\n'
     '    if panel_state != PANEL_SKIPPED and not convenable:\n'
     '        return None',
     '    pass'),
    ("gate: the missing kinds are taken on trust",
     '    if derived_missing != clean_missing:\n        return None',
     '    pass'),
    ("gate: the trigger state is taken on trust",
     '    if _trigger_state(ctx, clean) != trigger_state:\n        return None',
     '    pass'),
    ("gate: an accusation needs no words",
     '    if fraud_finding == FRAUD_INDICATORS_FOUND and fraud_quote == "":\n'
     '        return None',
     '    pass'),
    ("gate: a fraud answer nobody asked for is accepted",
     '            if isinstance(offered, str) \\\n'
     '                    and offered.strip().upper() != FRAUD_NOT_ASKED:',
     '            if False:'),
    ("verdict: an unassessed round is treated as a reading",
     '    if payload["panel_state"] != PANEL_ASSESSED:\n'
     '        return VERDICT_INCONCLUSIVE',
     '    pass'),
    ("verdict: an unavailable document is a reading",
     '    if payload["policy_status"] != EVIDENCE_REACHABLE \\\n'
     '            or payload["missing_required_kinds"]:\n'
     '        return VERDICT_EVIDENCE_UNAVAILABLE',
     '    pass'),
    ("verdict: an unsettled fraud question is upheld",
     '    if findings["fraud"]["finding"] == FRAUD_UNCLEAR:',
     '    if False:'),
    ("verdict: an evidenced exclusion is outranked",
     '    for row in findings["exclusions"]:\n'
     '        if row["finding"] == EXCLUSION_EVIDENCED:\n'
     '            return VERDICT_EXCLUSION_APPLIES\n'
     '    if findings["evidence"]["contradiction"]:\n'
     '        return VERDICT_INCONCLUSIVE',
     '    if findings["evidence"]["contradiction"]:\n'
     '        return VERDICT_INCONCLUSIVE'),
    ("verdict: evidence that addresses its reader may win coverage",
     '    if payload["directed_text_hits"] > 0:',
     '    if False:'),
    ("verdict: insufficient evidence is upheld",
     '    if not findings["evidence"]["sufficient"]:\n'
     '        return VERDICT_INCONCLUSIVE',
     '    pass'),
    ("verdict: an unclear condition is upheld",
     '    for row in findings["conditions"]:\n'
     '        if row["finding"] != CONDITION_MET:\n'
     '            return VERDICT_INCONCLUSIVE',
     '    pass'),
    ("verdict: a trigger that did not fire is upheld",
     '    if payload["trigger_state"] == TRIGGER_NOT_MET:\n'
     '        return VERDICT_COVERAGE_NOT_ESTABLISHED',
     '    pass'),
    ("trigger: the rule is inverted",
     '    if ctx["trigger"]["rule"] == RULE_AT_LEAST:\n'
     '        return TRIGGER_MET if value >= threshold else TRIGGER_NOT_MET\n'
     '    return TRIGGER_MET if value <= threshold else TRIGGER_NOT_MET',
     '    if ctx["trigger"]["rule"] == RULE_AT_LEAST:\n'
     '        return TRIGGER_MET if value <= threshold else TRIGGER_NOT_MET\n'
     '    return TRIGGER_MET if value >= threshold else TRIGGER_NOT_MET'),
    ("trigger: a measurement nobody found still counts",
     '    if not findings["trigger"]["value_found"]:\n'
     '        return TRIGGER_UNREADABLE',
     '    pass'),
    ("documents: the committed hash is not checked",
     '    if hashlib.sha256(body).hexdigest() != expected_sha:\n'
     '        return (EVIDENCE_UNAVAILABLE, REASON_HASH_MISMATCH, None, 0)',
     '    pass'),
    ("documents: the size cap is removed",
     'FETCH_BYTES_CAP = 200000',
     'FETCH_BYTES_CAP = 500000000'),
    ("documents: any location is admitted",
     '    if not isinstance(url, str):\n        return "URL_NOT_A_STRING"',
     '    return ""'),
    ("validator: everything the leader says is agreed with",
     'def _first_difference(own: dict, theirs: dict) -> str:',
     'def _first_difference(own: dict, theirs: dict) -> str:\n    return ""'),
    ('validator: the verdict is not compared',
     '                   "directed_text_hits", "panel_state", "trigger_state",\n                   "verdict"]',
     '                   "directed_text_hits", "panel_state", "trigger_state"]'),
    ('validator: the document statuses are not compared',
     '                   "evidence_digest", "policy_status", "policy_reason",\n                   "directed_text_hits",',
     '                   "evidence_digest",\n                   "directed_text_hits",'),
    ('validator: the document rows are not compared',
     '        for field in ["evidence_id", "kind", "status", "reason",\n                      "byte_count"]:',
     '        for field in []:'),
    ('gate: the verdict need not follow from the findings',
     '    if payload.get("verdict") != verdict:\n        return None',
     '    pass'),
    ('gate: the criteria need not follow from the findings',
     '    if payload.get("criteria") != criteria:\n        return None',
     '    pass'),
    ("lifecycle: a settled claim can be adjudicated again",
     '        if str(submission.status) != STATUS_PENDING:\n'
     '            self._reject("illegal transition from " '
     '+ str(submission.status))',
     '        pass'),
    ("lifecycle: rounds never run out",
     'MAX_ROUNDS = 3',
     'MAX_ROUNDS = 99'),
    ("lifecycle: anyone may publish a policy version",
     '        if gl.message.sender_address != current.owner:\n'
     '            self._reject("only the policy owner may publish a version")',
     '        pass'),
    ("lifecycle: anyone may cancel another party's claim",
     '        if gl.message.sender_address != submission.claimant:\n'
     '            self._reject("only the claimant may cancel a submission")',
     '        pass'),
    ("lifecycle: the claim deadline is not enforced",
     '        if _date_days(today) > _date_days(str(challenge.claim_deadline)):\n'
     '            self._reject("the claim deadline has passed")',
     '        pass'),
    ("lifecycle: the required kinds are not enforced",
     '            if kind not in offered:\n'
     '                self._reject("this challenge requires evidence of kind "\n'
     '                             + kind)',
     '            pass'),
    ("record: a retried claim counts twice",
     '        if submission.counted:\n            return\n'
     '        submission.counted = True',
     '        pass'),
    ("reliance: an unsettled claim is consumable",
     '        if str(submission.verdict) not in CONSUMABLE_VERDICTS:\n'
     '            return False\n'
     '        return self._freshness(submission, as_of) == FRESH_RELIABLE',
     '        return True'),
    ("reliance: a verdict never goes stale",
     '        if age > int(version.review_window_days):\n'
     '            return FRESH_STALE',
     '        pass'),
    ("reliance: a revoked policy version blocks nothing",
     '        if bool(version.revoked):\n            return FRESH_BLOCKED',
     '        pass'),
]


def run_suite(contract_path: pathlib.Path) -> bool:
    """True when the suite passes against this contract."""
    import os
    env = dict(os.environ)
    env["CLAIMCOURT_CONTRACT"] = str(contract_path)
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/direct", "-x", "-q",
         "--no-header", "-p", "no:cacheprovider"],
        cwd=str(ROOT), env=env, capture_output=True, text=True)
    return result.returncode == 0


def main() -> int:
    needle = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    source = CONTRACT.read_text(encoding="utf-8")
    killed = []
    survived = []
    broken = []
    work = tempfile.mkdtemp(prefix="claimcourt-mutants-")
    print("baseline: running the suite against the committed contract",
          flush=True)
    if not run_suite(CONTRACT):
        print("the suite does not pass unmutated; fix that first")
        return 1
    print("baseline PASS\n", flush=True)
    for index, (label, find, replace) in enumerate(MUTATIONS):
        if needle and needle not in label.lower():
            continue
        if source.count(find) != 1:
            broken.append(label)
            print("SKIP     %s (pattern occurs %d times)"
                  % (label, source.count(find)), flush=True)
            continue
        mutant = pathlib.Path(work) / ("mutant_%02d.py" % index)
        mutant.write_text(source.replace(find, replace), encoding="utf-8")
        passed = run_suite(mutant)
        if passed:
            survived.append(label)
            print("SURVIVED %s" % label, flush=True)
        else:
            killed.append(label)
            print("killed   %s" % label, flush=True)
    shutil.rmtree(work, ignore_errors=True)
    total = len(killed) + len(survived)
    print("\n%d/%d mutants killed" % (len(killed), total))
    if broken:
        print("%d pattern(s) no longer match the source: %s"
              % (len(broken), ", ".join(broken)))
    for label in survived:
        print("SURVIVED: " + label)
    return 0 if not survived and not broken else 1


if __name__ == "__main__":
    sys.exit(main())
