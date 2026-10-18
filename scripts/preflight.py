#!/usr/bin/env python3
"""Zero-dependency source invariants for ClaimCourt.

This runs with nothing installed: no GenLayer packages, no pytest, no
network. It does not replace Direct Mode or the GenVM linter - it catches
the class of mistake that is cheap to make and expensive to find on a
network, and it prints a real count of the assertions it actually ran.

    python scripts/preflight.py
"""

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "fixtures"

WRITES = ["register_policy", "publish_policy_version",
          "revoke_policy_version", "open_claim_challenge",
          "cancel_claim_challenge", "submit_claim", "resolve_submission",
          "retry_submission", "cancel_submission"]

VIEWS = ["get_config", "get_policy", "get_claim", "get_claim_status",
         "get_policy_hash", "get_policy_version", "get_submission",
         "get_verdict", "get_evidence_status", "get_findings", "get_receipt",
         "is_coverage_supported", "freshness", "is_fresh", "is_consumable",
         "claim_outcome", "policy_record", "list_submissions",
         "evidence_first_seen", "get_stats"]

VERDICTS = ["COVERAGE_SUPPORTED", "COVERAGE_NOT_ESTABLISHED",
            "EXCLUSION_APPLIES", "FRAUD_INDICATORS_FOUND", "INCONCLUSIVE",
            "EVIDENCE_UNAVAILABLE", "CANCELLED", "PENDING"]

FINDINGS = ["MET", "NOT_MET", "UNCLEAR", "NOT_ASSESSED", "EVIDENCED",
            "NOT_EVIDENCED", "INDICATORS_FOUND", "NO_INDICATORS",
            "NOT_ASKED"]

DOC_STATUSES = ["EVIDENCE_REACHABLE", "EVIDENCE_UNAVAILABLE",
                "EVIDENCE_INSUFFICIENT", "EVIDENCE_CONTRADICTORY",
                "EVIDENCE_SUFFICIENT"]

ROW_REASONS = ["FETCH_FAILED", "HASH_MISMATCH", "TOO_LARGE", "UNREADABLE"]

TRIGGER_STATES = ["NOT_DECLARED", "MET", "NOT_MET", "UNREADABLE"]

FORBIDDEN_IMPORTS = ["import time", "import random", "import requests",
                     "import urllib", "import socket", "import subprocess",
                     "import os", "from os ", "from time ", "from random ",
                     "import datetime", "from datetime "]

FIXTURE_FILES = ["policy-property-v1.txt", "policy-crop-parametric-v1.txt",
                 "incident-report-storm.txt", "repair-invoice-storm.txt",
                 "assessor-report-gradual.txt",
                 "incident-report-no-forced-entry.txt",
                 "incident-report-directed.txt",
                 "rainfall-record-season.txt",
                 "holding-statement-groundnut.txt",
                 "weather-observation-storm.txt"]

SECRET_HINTS = ["private_key", "privatekey", "mnemonic", "seed phrase",
                "BEGIN RSA", "gh_token", "github_token", "api_key"]


class Checks:
    def __init__(self):
        self.ran = 0
        self.failed = []

    def ok(self, condition, label):
        self.ran += 1
        if not condition:
            self.failed.append(label)

    def report(self):
        for label in self.failed:
            print("FAIL  " + label)
        passed = self.ran - len(self.failed)
        print("%d/%d PASS" % (passed, self.ran))
        return 0 if not self.failed else 1


def main() -> int:
    checks = Checks()

    sources = sorted(CONTRACTS.glob("*.py"))
    checks.ok(len(sources) == 1,
              "exactly one deployable contract under contracts/")
    if len(sources) != 1:
        return checks.report()
    source = sources[0]
    text = source.read_text(encoding="utf-8")
    lines = text.split("\n")

    # -- the header GenVM parses before anything else ----------------------
    checks.ok(lines[0].startswith("# v"), "line 1 is a version comment")
    checks.ok('"Depends"' in lines[1], "line 2 carries the Depends metadata")
    checks.ok(re.search(r'py-genlayer:[0-9a-z]{40,}', lines[1]) is not None,
              "the runner is pinned to an explicit version hash")
    checks.ok("latest" not in lines[1] and "test" not in lines[1],
              "the runner pin is not a local-only alias")
    checks.ok(lines[2].strip() == "",
              "line 3 is blank, so the Depends block ends cleanly")

    # -- imports and forbidden nondeterminism ------------------------------
    checks.ok("from genlayer import *" in text, "the SDK is imported")
    for forbidden in FORBIDDEN_IMPORTS:
        checks.ok(forbidden not in text, "no " + forbidden.strip())
    checks.ok("eval(" not in text, "no eval")
    checks.ok(re.search(r"\bexec\(", text) is None, "no exec")
    checks.ok("json.loads" in text, "model output is parsed with json.loads")

    # -- the public surface -------------------------------------------------
    for name in WRITES:
        checks.ok(re.search(r"@gl\.public\.write\s+def " + name + r"\(",
                            text) is not None,
                  "write " + name + " is public")
    for name in VIEWS:
        checks.ok(re.search(r"@gl\.public\.view\s+def " + name + r"\(",
                            text) is not None,
                  "view " + name + " is public")
    checks.ok(text.count("@gl.public.write") == len(WRITES),
              "no undeclared public write")
    checks.ok(text.count("@gl.public.view") == len(VIEWS),
              "no undeclared public view")

    # -- the enums a consumer depends on ------------------------------------
    for verdict in VERDICTS:
        checks.ok('"' + verdict + '"' in text,
                  "verdict " + verdict + " is defined")
    for finding in FINDINGS:
        checks.ok('"' + finding + '"' in text,
                  "finding " + finding + " is defined")
    for status in DOC_STATUSES:
        checks.ok('"' + status + '"' in text,
                  "evidence status " + status + " is defined")
    for reason in ROW_REASONS:
        checks.ok('"' + reason + '"' in text,
                  "unavailability reason " + reason + " is defined")
    for state in TRIGGER_STATES:
        checks.ok('"' + state + '"' in text,
                  "trigger state " + state + " is defined")

    # -- nondeterminism lives in one place ---------------------------------
    checks.ok(text.count("gl.vm.run_nondet_unsafe(") == 1,
              "exactly one consensus round in the contract")
    checks.ok(text.count("gl.nondet.web.get(") == 1,
              "documents are fetched in one helper")
    checks.ok("def _trigger_state(" in text,
              "a parametric trigger is compared in code, not by the model")
    checks.ok("Do not decide whether it " in text,
              "the panel is told not to decide the trigger")
    checks.ok("Missing or incomplete evidence is never" in text,
              "the panel is told that a gap is not an indicator of fraud")
    checks.ok(text.count("gl.nondet.exec_prompt(") == 1,
              "the panel is convened in one place")
    checks.ok("def validator_fn(leader_res)" in text,
              "a custom validator is supplied to the round")
    checks.ok("_validator_decision(leader_res" in text,
              "the validator runs the contract's own gate")
    nondet_region = text[text.index("def _fetch_doc("):
                         text.index("def _parse_payload(")]
    checks.ok(nondet_region.count("gl.nondet.") == 2,
              "every nondeterministic call is inside the node procedure")

    # -- the gate and the derivation ----------------------------------------
    for marker in ["def _parse_payload(", "def _first_difference(",
                   "def _quote_grounded(", "def _derive_verdict(",
                   "def _criteria(", "def _evidence_status(",
                   "def _admit_url(", "def _exact_bool(",
                   "def _apply_grounding(", "def _directed_text_hits("]:
        checks.ok(marker in text, marker.strip("def (") + " exists")
    derivation = text[text.index("def _derive_verdict("):]
    derivation = derivation[:derivation.index("# == storage")]
    order = [derivation.index("VERDICT_EVIDENCE_UNAVAILABLE"),
             derivation.index("VERDICT_FRAUD_INDICATORS_FOUND"),
             derivation.index("VERDICT_EXCLUSION_APPLIES"),
             derivation.index("VERDICT_COVERAGE_NOT_ESTABLISHED"),
             derivation.index("VERDICT_COVERAGE_SUPPORTED")]
    checks.ok(order == sorted(order),
              "verdict precedence runs from unavailable to supported")
    checks.ok("directed_text_hits" in derivation,
              "evidence that addresses its reader cannot win coverage")
    checks.ok("FRAUD_INDICATORS_FOUND" in derivation,
              "fraud is only ever a declared, quoted finding")
    checks.ok("isinstance(value, bool)" in text,
              "booleans are checked for exactly, not truthily")

    # -- bounds -------------------------------------------------------------
    for name, lower, upper in [("MAX_CONDITIONS", 1, 20),
                               ("MAX_EXCLUSIONS", 1, 20),
                               ("MAX_EVIDENCE", 1, 20),
                               ("MAX_REQUIRED_KINDS", 1, 20),
                               ("MAX_ROUNDS", 1, 10),
                               ("MAX_SUBMISSIONS_PER_CHALLENGE", 1, 10000),
                               ("MAX_VERSIONS", 1, 1000),
                               ("URL_MAX", 50, 2048),
                               ("QUOTE_MAX", 40, 2000),
                               ("QUOTE_MIN", 4, 100),
                               ("FETCH_BYTES_CAP", 1000, 5000000),
                               ("POLICY_CHARS", 500, 100000),
                               ("DOCUMENT_CHARS", 500, 100000)]:
        found = re.search("^" + name + r" = (\d+)$", text, re.MULTILINE)
        checks.ok(found is not None and lower <= int(found.group(1)) <= upper,
                  name + " is set and within a sane range")

    # -- fixtures are honest about what they are ---------------------------
    for name in FIXTURE_FILES:
        path = FIXTURES / name
        checks.ok(path.exists(), "fixture " + name + " exists")
        if path.exists():
            body = path.read_text(encoding="utf-8")
            checks.ok("TEST / DEMONSTRATION ONLY" in body,
                      "fixture " + name + " is marked for demonstration")
            checks.ok("NOT FOR PRODUCTION" in body,
                      "fixture " + name + " is marked not for production")
            checks.ok(b"\r\n" not in path.read_bytes(),
                      "fixture " + name + " has stable line endings")

    # -- nothing that looks like a secret ----------------------------------
    for hint in SECRET_HINTS:
        checks.ok(hint.lower() not in text.lower(),
                  "no " + hint + " in the contract")

    return checks.report()


if __name__ == "__main__":
    sys.exit(main())
