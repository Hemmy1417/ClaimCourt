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
     "    return flat_quote in _flat(text)",
     "    return True"),
    ("grounding: a one-word quote counts",
     "QUOTE_MIN = 12",
     "QUOTE_MIN = 0"),
    ("types: an integer passes for a boolean",
     "def _exact_bool(value):\n    if isinstance(value, bool):",
     "def _exact_bool(value):\n    if isinstance(value, int):"),
    ("types: an unknown supported value is kept",
     '        if supported not in ["YES", "NO", "UNCLEAR"]:\n'
     "            return None\n        out.append({",
     "        out.append({"),
    ("gate: the leader names its own outcome",
     "            if _ground_outcome(checked) != outcome:\n"
     "                return None",
     "            pass"),
    ("gate: an unread round may carry findings",
     "            if located or stated or clause_quote != \"\" "
     "or notice_quote != \"\" \\\n                    or exceeded "
     'or supported != "UNCLEAR" \\\n'
     "                    or outcome != GROUND_UNDECIDED:\n"
     "                return None",
     "            pass"),
    ("gate: the payload need not be bound to this review",
     '    if payload.get("review_id") != ctx["review_id"]:\n        '
     "return None",
     "    pass"),
    ("gate: the panel state need not match the documents",
     "    if panel_state != PANEL_SKIPPED and (policy_status != DOC_EXAMINED\n"
     "                                         or notice_status "
     "!= DOC_EXAMINED):\n        return None",
     "    pass"),
    ("verdict: a notice may address its reader and still be upheld",
     '    if payload["directed_text_hits"] > 0:\n'
     "        return VERDICT_INCONCLUSIVE",
     "    pass"),
    ("verdict: an unread round is treated as a reading",
     '    if payload["panel_state"] != PANEL_READ:\n'
     "        return VERDICT_INCONCLUSIVE",
     "    pass"),
    ("verdict: a misstated ground is outranked",
     "    if GROUND_NOT_IN_NOTICE in outcomes:\n"
     "        return VERDICT_MISSTATED\n"
     "    if GROUND_CLAUSE_ABSENT in outcomes:\n"
     "        return VERDICT_MISCITED",
     "    if GROUND_CLAUSE_ABSENT in outcomes:\n"
     "        return VERDICT_MISCITED\n"
     "    if GROUND_NOT_IN_NOTICE in outcomes:\n"
     "        return VERDICT_MISSTATED"),
    ("verdict: an undecided ground is upheld",
     '    if row["supported"] == "UNCLEAR":\n        return GROUND_UNDECIDED',
     "    pass"),
    ("verdict: an unavailable document is a reading",
     '    if payload["policy_status"] != DOC_EXAMINED \\\n'
     '            or payload["notice_status"] != DOC_EXAMINED:\n'
     "        return VERDICT_UNAVAILABLE",
     "    pass"),
    ("documents: the committed hash is not checked",
     '    if hashlib.sha256(body).hexdigest() != expected_sha:\n'
     "        return (DOC_HASH_MISMATCH, None)",
     "    pass"),
    ("documents: the size cap is removed",
     "FETCH_BYTES_CAP = 200000",
     "FETCH_BYTES_CAP = 500000000"),
    ("documents: any location is admitted",
     '    if not isinstance(url, str):\n        return "URL_NOT_A_STRING"',
     "    return \"\""),
    ("validator: everything the leader says is agreed with",
     "def _first_difference(own: dict, theirs: dict) -> str:",
     "def _first_difference(own: dict, theirs: dict) -> str:\n    return \"\""),
    ("validator: per-ground findings are not compared",
     '        for field in ["clause_ref", "clause_located",\n'
     '                      "ground_stated_in_notice", "supported",\n'
     '                      "scope_exceeded", "outcome"]:',
     '        for field in []:'),
    ("validator: a leader failure is always believed",
     "def _vote_on_leader_error(leader_res, reproduce) -> bool:",
     "def _vote_on_leader_error(leader_res, reproduce) -> bool:\n"
     "    return True"),
    ("validator: the document statuses are not compared",
     'DECISION_FIELDS = ["schema", "review_id", "round", "definition_hash",\n'
     '                   "policy_sha256", "notice_sha256", "policy_status",\n'
     '                   "notice_status", "directed_text_hits", '
     '"panel_state"]',
     'DECISION_FIELDS = ["schema", "review_id", "round"]'),
    ("lifecycle: a resolved review can be read again",
     '        if str(review.status) != STATUS_OPEN:\n            self._reject'
     '("illegal transition from " + str(review.status))',
     "        pass"),
    ("lifecycle: rounds never run out",
     "MAX_ROUNDS = 3",
     "MAX_ROUNDS = 99"),
    ("lifecycle: anyone may publish a clause version",
     "        if gl.message.sender_address != current.owner:\n"
     '            self._reject("only the clause set owner may publish a '
     'version")',
     "        pass"),
    ("lifecycle: anyone may withdraw another party's review",
     "        if gl.message.sender_address != review.opener:\n"
     '            self._reject("only the opener may withdraw a review")',
     "        pass"),
    ("lifecycle: the same notice can be reviewed twice",
     "        existing = self.notice_registry.get(str(notice_sha256))\n"
     '        if existing is not None and str(existing) != "":\n'
     '            self._reject("that notice is already under review as "\n'
     "                         + str(existing))",
     "        pass"),
    ("record: a retried review counts twice",
     "        if review.counted:\n            return\n"
     "        review.counted = True",
     "        pass"),
    ("reliance: an unsettled review is consumable",
     "        if str(review.verdict) not in [VERDICT_SUPPORTED, "
     "VERDICT_UNSUPPORTED,\n"
     "                                       VERDICT_OVERBROAD, "
     "VERDICT_MISCITED,\n"
     "                                       VERDICT_MISSTATED]:\n"
     "            return False\n"
     "        return self._freshness(review, as_of) == FRESH_RELIABLE",
     "        return True"),
    ("reliance: a verdict never goes stale",
     "        if age > int(version.review_window_days):\n"
     "            return FRESH_STALE",
     "        pass"),
    ("reliance: a revoked clause version still blocks nothing",
     "        if bool(version.revoked):\n            return FRESH_BLOCKED",
     "        pass"),
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
    print("baseline: running the suite against the committed contract")
    if not run_suite(CONTRACT):
        print("the suite does not pass unmutated; fix that first")
        return 1
    print("baseline PASS\n")
    for index, (label, find, replace) in enumerate(MUTATIONS):
        if needle and needle not in label.lower():
            continue
        if source.count(find) != 1:
            broken.append(label)
            print("SKIP     %s (pattern occurs %d times)"
                  % (label, source.count(find)))
            continue
        mutant = pathlib.Path(work) / ("mutant_%02d.py" % index)
        mutant.write_text(source.replace(find, replace), encoding="utf-8")
        passed = run_suite(mutant)
        if passed:
            survived.append(label)
            print("SURVIVED %s" % label)
        else:
            killed.append(label)
            print("killed   %s" % label)
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
