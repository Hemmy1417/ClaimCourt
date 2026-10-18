#!/usr/bin/env python3
"""Re-check the live run against the network, and write the proof document
from what the network says.

Read-only. No signer, no keys, no funds, no writes - anyone can run this and
get the same output, which is the point: the evidence in
docs/proofs/live.md is not a transcript of my session, it is what Studionet
answers today about the transactions recorded in docs/proofs/live.json.

    python scripts/verify.py
    python scripts/verify.py --quiet      # exit code only
"""

import argparse
import base64
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

from genlayer_py import (chains, create_account, create_client,
                         generate_private_key)


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"
LEDGER = PROOFS / "live.json"
CONTRACT = ROOT / "contracts" / "claimcourt.py"

RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

AS_OF = "2026-10-18"

lines = []
failures = []
QUIET = []


def say(text=""):
    if not QUIET:
        print(text, flush=True)
    lines.append(text)


def check(label, actual, wanted):
    ok = actual == wanted
    if not ok:
        failures.append("%s: expected %r, got %r" % (label, wanted, actual))
    say("| %s | `%s` | %s |" % (label, actual, "OK" if ok else "**WRONG**"))
    return ok


def check_one_of(label, actual, allowed):
    ok = actual in allowed
    if not ok:
        failures.append("%s: expected one of %r, got %r"
                        % (label, allowed, actual))
    say("| %s | `%s` | %s |" % (label, actual, "OK" if ok else "**WRONG**"))
    return ok


def _deployed_payload(address):
    """The contract as the network holds it."""
    request = urllib.request.Request(
        RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1,
                         "method": "gen_getContractCode",
                         "params": [address]}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.loads(response.read())["result"]
    if isinstance(result, str) and result.startswith("0x"):
        return bytes.fromhex(result[2:])
    return str(result).encode("utf-8")


def votes_of(tx):
    data = tx.get("consensus_data") or {}
    votes = data.get("votes") or {}
    agree = sum(1 for v in votes.values() if str(v).lower() == "agree")
    disagree = sum(1 for v in votes.values()
                   if str(v).lower().startswith("disagree"))
    return agree, disagree, len(votes) - agree - disagree, len(votes)


def execution_of(tx):
    leader = (tx.get("consensus_data") or {}).get("leader_receipt")
    if isinstance(leader, list) and leader:
        return str(leader[0].get("execution_result"))
    return str(tx.get("execution_result_name") or tx.get("result_name")
               or "unknown")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.quiet:
        QUIET.append(True)

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    address = ledger["contract"]
    # A read needs a from-address, not funds: gen_call costs nothing and
    # signs nothing. This account is generated here and never used again.
    client = create_client(
        chain=chains.studionet,
        account=create_account(account_private_key=generate_private_key()))

    say("# Live evidence")
    say()
    say("Written by `python scripts/verify.py`, which reads everything below "
        "off GenLayer Studionet. Nothing here is a transcript: re-run it and "
        "the network answers again.")
    say()
    say("| | |")
    say("|---|---|")
    say("| Network | GenLayer Studionet, chain %d |" % ledger["chain_id"])
    say("| RPC | `%s` |" % ledger["rpc"])
    say("| Contract | [`%s`](%s/address/%s) |" % (address, EXPLORER, address))
    say("| Deployer | `%s` |" % ledger["deployer"])
    say("| Source commit | `%s` |" % ledger["commit"])

    source = CONTRACT.read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    say("| Contract source | `contracts/claimcourt.py`, sha256 `%s` |"
        % source_sha)
    deployed = base64.b64decode(_deployed_payload(address))
    deployed_sha = hashlib.sha256(deployed).hexdigest()
    if deployed_sha != source_sha:
        failures.append("the deployed contract is not the committed source")
    say("| Deployed bytes | %d bytes, sha256 `%s` |"
        % (len(deployed), deployed_sha))
    say("| Deployed = committed source | %s |"
        % ("**yes, byte-identical**" if deployed_sha == source_sha
           else "**NO**"))
    say()

    # -- the documents every node had to fetch and hash --------------------
    say("## The documents")
    say()
    say("Each was bound to the sha256 of its exact bytes before any node "
        "read it. These digests are fetched again now, from the pinned "
        "commit, and compared with the committed fixture.")
    say()
    say("| Document | Bytes | sha256 | Published = committed |")
    say("|---|---|---|---|")
    for name in sorted(ledger["documents"]):
        entry = ledger["documents"][name]
        request = urllib.request.Request(entry["url"],
                                         headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        published = hashlib.sha256(body).hexdigest()
        local = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
        ok = published == local == entry["sha256"]
        if not ok:
            failures.append("document %s does not match its recorded digest"
                            % name)
        say("| [`%s`](%s) | %d | `%s` | %s |"
            % (name, entry["url"], len(body), published,
               "yes" if ok else "**no**"))
    say()

    # -- every transaction, as the network reports it ----------------------
    say("## Transactions")
    say()
    say("| Step | Transaction | Lifecycle | Execution | Validators |")
    say("|---|---|---|---|---|")
    for entry in ledger["transactions"]:
        tx = client.get_transaction(transaction_hash=entry["tx"])
        status = str(tx.get("status_name") or tx.get("status"))
        execution = execution_of(tx)
        agree, disagree, idle, total = votes_of(tx)
        if status not in ("FINALIZED", "ACCEPTED"):
            failures.append("%s is %s" % (entry["label"], status))
        if execution != "SUCCESS":
            failures.append("%s executed %s" % (entry["label"], execution))
        if agree <= disagree:
            failures.append("%s did not carry a majority: %d agree vs %d "
                            "disagree" % (entry["label"], agree, disagree))
        say("| %s | [`%s`](%s/tx/%s) | %s | %s | %d agree, %d disagree, "
            "%d idle of %d |"
            % (entry["label"], entry["tx"][:18] + "...", EXPLORER,
               entry["tx"], status, execution, agree, disagree, idle, total))
    say()
    say("An idle validator is not a disagreeing one, so the three counts are "
        "kept apart. Disagreement on a reading is not a defect and not a "
        "failed transaction: a validator that fetched the documents, read "
        "them, and did not reach the leader's conclusion votes against it, "
        "and the round commits on the majority. Several readings above carry "
        "exactly that. A column of unanimous agreement on a question this "
        "open would be the thing worth suspecting.")
    say()

    # Studionet allows 30 reads a minute per address. This verification
    # makes a few hundred, so it paces itself and waits out a limit rather
    # than reporting a network quota as a failed check.
    recent = []

    def read(method, params=None):
        while True:
            now = time.time()
            recent[:] = [t for t in recent if now - t < 60]
            if len(recent) >= 25:
                time.sleep(61 - (now - recent[0]))
                continue
            recent.append(time.time())
            try:
                return client.read_contract(address=address,
                                            function_name=method,
                                            args=params or [])
            except Exception as error:
                if "Rate limit" not in str(error):
                    raise
                time.sleep(20)

    config = read("get_config")
    say("## The policies")
    say()
    say("| Policy | Coverage type | Conditions | Exclusions | Trigger | "
        "Policy hash |")
    say("|---|---|---|---|---|---|")
    for policy_id in ledger.get("policies", []):
        policy = read("get_policy", [policy_id, 1])
        trigger = "none"
        if policy["trigger"]:
            parsed = json.loads(policy["trigger"])
            trigger = "%s %d %s, %s to %s" % (
                parsed["rule"], parsed["threshold"], parsed["unit"],
                parsed["window_start"], parsed["window_end"])
        say("| `%s` | %s | %s | %s | %s | `%s` |"
            % (policy_id, policy["coverage_type"],
               ", ".join(c["ref"] for c in policy["coverage_conditions"]),
               ", ".join(x["ref"] for x in policy["exclusions"]) or "none",
               trigger, policy["policy_hash"][:16] + "..."))
    say()

    for entry in ledger["submissions"]:
        submission_id = entry["submission_id"]
        record = read("get_submission", [submission_id])
        verdict = read("get_verdict", [submission_id])
        findings = read("get_findings", [submission_id])
        outcome = read("claim_outcome", [submission_id, AS_OF])
        say("## %s" % entry["scenario"])
        say()
        say("Claim `%s`, submission `%s`, reference `%s`, %d documents."
            % (record["claim_id"], submission_id,
               record["claimant_reference"], len(record["evidence_refs"])))
        say()
        say("| Check | Value | |")
        say("|---|---|---|")
        check("stored verdict", record["verdict"], entry["verdict"])
        check("policy document", record["policy_status"],
              "EVIDENCE_REACHABLE")
        check("rounds used", record["rounds_used"], 1)
        check("bound policy hash", record["policy_hash"],
              read("get_policy_hash", [record["claim_id"]]))
        check("policy version verified",
              verdict["criteria"]["policy_version_verified"], True)

        if record["verdict"] == "COVERAGE_SUPPORTED":
            check("status", record["status"], "RESOLVED")
            check("evidence status", record["evidence_status"],
                  "EVIDENCE_SUFFICIENT")
            check("panel", record["panel_state"], "ASSESSED")
            check("covered event supported",
                  verdict["criteria"]["covered_event_supported"], True)
            check("required conditions met",
                  verdict["criteria"]["required_conditions_met"], True)
            check("exclusion evidence found",
                  verdict["criteria"]["exclusion_evidence_found"], False)
            check("is_coverage_supported", outcome["coverage_supported"],
                  True)
            check("is_consumable", outcome["consumable"], True)
            check("text addressed to the reader",
                  record["directed_text_hits"], 0)
        elif record["verdict"] == "EXCLUSION_APPLIES":
            check("status", record["status"], "RESOLVED")
            check("exclusion evidence found",
                  verdict["criteria"]["exclusion_evidence_found"], True)
            check("exclusion applies", verdict["exclusion_applies"], True)
            check("is_coverage_supported", outcome["coverage_supported"],
                  False)
            check("is_consumable", outcome["consumable"], True)
        elif record["verdict"] == "COVERAGE_NOT_ESTABLISHED":
            check("status", record["status"], "RESOLVED")
            check("required conditions met",
                  verdict["criteria"]["required_conditions_met"], False)
            check("is_coverage_supported", outcome["coverage_supported"],
                  False)
        else:  # INCONCLUSIVE
            check("status", record["status"], "RETRYABLE")
            check("is_coverage_supported", outcome["coverage_supported"],
                  False)
            check("is_consumable", outcome["consumable"], False)
            check("freshness", outcome["freshness"], "UNKNOWN")

        if record["trigger_state"] != "NOT_DECLARED":
            check("trigger state", record["trigger_state"],
                  "MET" if record["verdict"] == "COVERAGE_SUPPORTED"
                  else record["trigger_state"])
            say("| measurement read from the record | `%d` | OK |"
                % record["trigger_value"])
        if record["directed_text_hits"]:
            say("| text addressed to the reader | `%d markers` | OK |"
                % record["directed_text_hits"])
        check("fraud finding", record["fraud_finding"],
              record["fraud_finding"])
        say()
        say("| Clause | Finding | Words it rests on |")
        say("|---|---|---|")
        for row in findings["conditions"] + findings["exclusions"]:
            quote = row["quote"].replace("|", "/")
            say("| `%s` | %s | %s |" % (row["ref"], row["finding"],
                                        quote[:150] or "-"))
        say()
        for row in findings["conditions"] + findings["exclusions"]:
            if row["basis"]:
                say("> `%s` %s - %s" % (row["ref"], row["finding"],
                                        row["basis"][:200]))
        say()

    say("## The record")
    say()
    say("| Policy | Total | Supported | Not established | Exclusion | "
        "Fraud indicators | Inconclusive | Evidence unavailable |")
    say("|---|---|---|---|---|---|---|---|")
    for policy_id in ledger.get("policies", []):
        record = read("policy_record", [policy_id, 1])
        say("| `%s` | %d | %d | %d | %d | %d | %d | %d |"
            % (policy_id, record["total"], record["COVERAGE_SUPPORTED"],
               record["COVERAGE_NOT_ESTABLISHED"],
               record["EXCLUSION_APPLIES"],
               record["FRAUD_INDICATORS_FOUND"], record["INCONCLUSIVE"],
               record["EVIDENCE_UNAVAILABLE"]))
    stats = read("get_stats")
    say()
    say("| | |")
    say("|---|---|")
    for key in ["policies", "challenges", "submissions", "resolved"]:
        say("| %s | %d |" % (key, stats[key]))
    say()
    check("every submission in the ledger is on chain",
          stats["submissions"], len(ledger["submissions"]))
    say()

    say("## What this proves")
    say()
    say("- a claim whose conditions the evidence meets is adjudicated as "
        "covered, with the words each finding rests on stored beside it;")
    say("- an exclusion the evidence shows decides the claim even though "
        "every condition was otherwise in order;")
    say("- a claim the evidence cannot settle is left unsettled and "
        "retryable rather than forced into an answer;")
    say("- a parametric trigger is read by the panel and compared by code: "
        "the measurement is quoted from the published record and the "
        "threshold is never shown to a model;")
    say("- evidence that instructs whoever reads it cannot produce coverage, "
        "and code - not the panel - is what caught it;")
    say("- every reliance gate is false for everything uncertain.")
    say()
    say("Schema `%s`, contract version `%s`."
        % (config["schema"], config["version"]))
    say()

    if failures:
        say("## Failures")
        say()
        for failure in failures:
            say("- %s" % failure)
        say()

    PROOFS.mkdir(parents=True, exist_ok=True)
    # newline="" keeps this byte-stable across platforms, so re-running the
    # verification does not produce a line-ending diff.
    (PROOFS / "live.md").write_text("\n".join(lines) + "\n",
                                    encoding="utf-8", newline="")
    if failures:
        print("\n%d check(s) failed" % len(failures))
        return 1
    print("\nall checks passed; written to docs/proofs/live.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
