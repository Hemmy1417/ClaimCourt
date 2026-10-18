#!/usr/bin/env python3
"""Live evidence driver for hosted Studionet.

Deploys `contracts/claimcourt.py` as it stands, then adjudicates synthetic
claims against real validators reading real documents: a claim that
satisfies its policy, a claim an exclusion answers, a claim whose condition
is not met, a parametric claim whose trigger is compared in code, and a
claim whose evidence instructs whoever reads it. Every transaction hash,
every stored result and every assertion is printed.

    python scripts/live.py --commit <sha>                  deploy and run all
    python scripts/live.py --commit <sha> --address 0x...  reuse a deployment
    python scripts/live.py --commit <sha> --scenarios a,b

The fixtures must already be pushed: the documents are read from
raw.githubusercontent.com at the commit given, so the bytes the validators
fetch are pinned and cannot change under an adjudication.

A signer comes from CLAIMCOURT_SIGNER_KEY when it is set; otherwise a
throwaway account is generated and funded from the Studionet faucet. No key
is ever printed.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

from genlayer_py import (chains, create_account, create_client,
                         generate_private_key)
from genlayer_py.types import TransactionStatus


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "claimcourt.py"
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"

RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
RAW = "https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/%s/fixtures/%s"

POLICY_PROPERTY = "policy-property-v1.txt"
POLICY_CROP = "policy-crop-parametric-v1.txt"
STORM_REPORT = "incident-report-storm.txt"
STORM_INVOICE = "repair-invoice-storm.txt"
GRADUAL_REPORT = "assessor-report-gradual.txt"
NO_ENTRY_REPORT = "incident-report-no-forced-entry.txt"
DIRECTED_REPORT = "incident-report-directed.txt"
RAINFALL_RECORD = "rainfall-record-season.txt"
HOLDING_STATEMENT = "holding-statement-groundnut.txt"
STORM_OBSERVATION = "weather-observation-storm.txt"

DOCUMENTS = [POLICY_PROPERTY, POLICY_CROP, STORM_REPORT, STORM_INVOICE,
             GRADUAL_REPORT, NO_ENTRY_REPORT, DIRECTED_REPORT,
             RAINFALL_RECORD, HOLDING_STATEMENT, STORM_OBSERVATION]

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

TRANSIENT_MARKERS = ["BAD_RECORD_MAC", "RemoteDisconnected", "ConnectionReset",
                     "Connection aborted", "timed out", "<!DOCTYPE html>",
                     "502", "503", "504", "EOF occurred"]

DEADLINE = "2027-06-30"
AS_OF = "2026-10-18"

log_lines = []


def say(text=""):
    print(text, flush=True)
    log_lines.append(text)


# -- the policies ------------------------------------------------------------

PROPERTY_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "A covered event under clause 1 occurred at the insured "
                 "premises during the period of insurance and caused the "
                 "damage claimed."},
        {"ref": "C2",
         "text": "The loss was reported to the insurer within thirty days "
                 "of the insured becoming aware of it, and the record shows "
                 "when they became aware."},
        {"ref": "C3",
         "text": "The cost of reinstatement for the items claimed is "
                 "evidenced by an invoice, an estimate or an assessor's "
                 "figure."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The damage is the result of gradual deterioration, wear "
                 "and tear, rot, corrosion or lack of maintenance over "
                 "time, rather than a sudden event."},
        {"ref": "X2",
         "text": "The premises were left unoccupied for more than sixty "
                 "consecutive days immediately before the loss."},
    ],
    "review_window_days": 365,
}

THEFT_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "A covered event under clause 1 occurred at the insured "
                 "premises during the period of insurance and caused the "
                 "loss claimed."},
        {"ref": "C4",
         "text": "For a theft claim there is evidence of forcible and "
                 "violent entry to the premises. Entry by a door or window "
                 "left open or unlocked is not forcible and violent entry."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The loss is the result of gradual deterioration, wear and "
                 "tear or lack of maintenance over time."},
    ],
    "review_window_days": 365,
}

CROP_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "The claim is made for the holding named in the schedule "
                 "and identifies the station and window the schedule "
                 "names."},
        {"ref": "C2",
         "text": "The claim is supported by the published rainfall record "
                 "for that station and window, as issued by the publishing "
                 "body."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The loss was caused by pests, disease, fire, theft or "
                 "civil disturbance rather than by the measured rainfall "
                 "shortfall."},
    ],
    "trigger": {
        "measure": "cumulative rainfall at the synthetic reference station",
        "unit": "millimetres",
        "rule": "AT_MOST",
        "threshold": 220,
        "window_start": "2026-06-01",
        "window_end": "2026-09-30",
    },
    "review_window_days": 365,
}

STORM_INCIDENT = {
    "incident_summary": "A storm on the night of 2 to 3 March 2026 lifted "
                        "the roof covering and water entered the stockroom, "
                        "damaging racking, stock and ceiling panels.",
    "incident_date": "2026-03-03",
    "incident_location_reference": "SYN-UNIT-4",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}

GRADUAL_INCIDENT = {
    "incident_summary": "Water damage to the stockroom ceiling and to goods "
                        "stored beneath it, claimed as storm damage on 14 "
                        "June 2026.",
    "incident_date": "2026-06-14",
    "incident_location_reference": "SYN-UNIT-9",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}

THEFT_INCIDENT = {
    "incident_summary": "Stock and a laptop were found missing from the "
                        "unit on the morning of 29 July 2026.",
    "incident_date": "2026-07-29",
    "incident_location_reference": "SYN-UNIT-12",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}

CROP_INCIDENT = {
    "incident_summary": "The 2026 growing window closed with recorded "
                        "rainfall below the level the schedule insures "
                        "against at the named station.",
    "incident_date": "2026-09-30",
    "incident_location_reference": "SYN-PLOT-7",
    "claimed_loss_category": "parametric drought",
    "claimed_amount_band": "fixed payout",
}


# -- transport ---------------------------------------------------------------

def harden_provider():
    """Retry transport failures only. A JSON-RPC error is a real answer and
    is never retried; a dropped socket or a CDN error page is not."""
    from genlayer_py.provider.provider import GenLayerProvider

    original = GenLayerProvider.make_request

    def patched(self, method, params):
        last = None
        for attempt in range(6):
            try:
                return original(self, method, params)
            except Exception as error:  # transport only
                text = str(error)
                if not any(marker in text for marker in TRANSIENT_MARKERS):
                    raise
                last = error
                time.sleep(2 + attempt * 2)
        raise last

    GenLayerProvider.make_request = patched


def rpc(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": params}).encode("utf-8")
    request = urllib.request.Request(
        RPC, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def published(commit, name):
    """(url, sha256, size) for the bytes a validator will actually fetch."""
    url = RAW % (commit, name)
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    digest = hashlib.sha256(body).hexdigest()
    local = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
    if digest != local:
        raise SystemExit("published %s does not match the local file "
                         "(%s vs %s)" % (name, digest, local))
    return url, digest, len(body)


# -- chain -------------------------------------------------------------------

def signer():
    import os
    key = os.environ.get("CLAIMCOURT_SIGNER_KEY")
    if key:
        account = create_account(account_private_key=key)
        say("signer: provided through the environment, %s" % account.address)
        return account, False
    account = create_account(account_private_key=generate_private_key())
    say("signer: generated for this run, %s" % account.address)
    return account, True


def fund(address):
    result = rpc("sim_fundAccount", [address, 500000000000000000000])
    if "error" in result:
        raise SystemExit("faucet refused: %s" % result["error"])
    say("faucet: funded %s" % address)
    time.sleep(3)


def consensus_summary(receipt):
    """Agreement as the receipt records it. An idle validator is not a
    disagreeing one, and collapsing the two would overstate dissent as
    easily as it would hide it."""
    data = receipt.get("consensus_data") or {}
    votes = data.get("votes") or {}
    if not votes:
        return "no votes recorded"
    agree = sum(1 for v in votes.values() if str(v).lower() == "agree")
    disagree = sum(1 for v in votes.values()
                   if str(v).lower().startswith("disagree"))
    other = len(votes) - agree - disagree
    return "%d agree, %d disagree, %d idle of %d" % (
        agree, disagree, other, len(votes))


def execution_result(receipt):
    """On this network the top-level execution_result is empty; the real
    value is on the leader receipt."""
    named = receipt.get("execution_result_name") or receipt.get("result_name")
    leader = (receipt.get("consensus_data") or {}).get("leader_receipt")
    if isinstance(leader, list) and leader:
        return str(leader[0].get("execution_result") or named or "unknown")
    return str(named or "unknown")


def lifecycle(receipt):
    return str(receipt.get("status_name") or receipt.get("status"))


def revert_reason(receipt):
    try:
        leader = receipt.get("consensus_data", {}).get("leader_receipt")
        if isinstance(leader, list) and leader:
            return str(leader[0].get("result", {}).get("payload", ""))[:300]
    except Exception:
        pass
    return ""


def _hex(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


class Chain:
    def __init__(self, account):
        self.client = create_client(chain=chains.studionet, account=account)
        self.account = account
        self.transactions = []
        self.address = ""

    def deploy(self):
        code = CONTRACT.read_bytes()
        say("deploying %d bytes, sha256 %s"
            % (len(code), hashlib.sha256(code).hexdigest()))
        tx_hash = self.client.deploy_contract(code=code.decode("utf-8"),
                                              args=[],
                                              consensus_max_rotations=3)
        receipt = self.client.wait_for_transaction_receipt(
            transaction_hash=tx_hash, status=TransactionStatus.ACCEPTED,
            interval=5000, retries=80)
        address = ((receipt.get("data") or {}).get("contract_address")
                   or ((receipt.get("tx_data_decoded") or {})
                       .get("contract_address")))
        if not address:
            raise SystemExit("no contract address in the receipt: %s"
                             % json.dumps(receipt)[:400])
        result = execution_result(receipt)
        say("deploy tx %s" % _hex(tx_hash))
        say("deploy lifecycle %s, execution %s, %s"
            % (lifecycle(receipt), result, consensus_summary(receipt)))
        if result.upper().endswith("ERROR"):
            raise SystemExit("deployment executed with an error: %s"
                             % revert_reason(receipt))
        self.address = address
        self.transactions.append(("deploy", _hex(tx_hash)))
        say("contract %s" % address)
        say("explorer %s/address/%s" % (EXPLORER, address))
        return address, _hex(tx_hash)

    def bind(self, address):
        self.address = address
        say("reusing deployment %s" % address)

    def write(self, method, args, label):
        tx_hash = self.client.write_contract(
            address=self.address, function_name=method, args=args,
            consensus_max_rotations=3)
        receipt = self.client.wait_for_transaction_receipt(
            transaction_hash=tx_hash, status=TransactionStatus.ACCEPTED,
            interval=5000, retries=100)
        result = execution_result(receipt)
        say("  %-26s tx %s  %s  %s"
            % (label, _hex(tx_hash), result, consensus_summary(receipt)))
        if result.upper().endswith("ERROR"):
            say("  revert: %s" % revert_reason(receipt))
            raise SystemExit("%s failed on chain" % label)
        self.transactions.append((label, _hex(tx_hash)))
        return _hex(tx_hash), receipt

    def read(self, method, args=None):
        return self.client.read_contract(address=self.address,
                                         function_name=method,
                                         args=args or [])

    def finality(self, tx_hash):
        tx = self.client.get_transaction(transaction_hash=tx_hash)
        return lifecycle(tx), execution_result(tx), consensus_summary(tx)


# -- the run -----------------------------------------------------------------

def expect(label, actual, wanted):
    ok = actual == wanted
    say("    %-42s %s  (%s)" % (label, "OK" if ok else "WRONG", actual))
    if not ok:
        raise SystemExit("%s: expected %r, got %r" % (label, wanted, actual))


def expect_one_of(label, actual, allowed):
    """Where more than one reading of the same documents is defensible, the
    assertion is on what the primitive guarantees - that the claim does not
    silently become covered - rather than on which reading a panel
    prefers."""
    ok = actual in allowed
    say("    %-42s %s  (%s)" % (label, "OK" if ok else "WRONG", actual))
    if not ok:
        raise SystemExit("%s: expected one of %r, got %r"
                         % (label, allowed, actual))


def evidence_list(docs, documents):
    out = []
    for evidence_id, kind, name in docs:
        url, digest, _size = documents[name]
        out.append({"evidence_id": evidence_id, "kind": kind, "url": url,
                    "sha256": digest})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True,
                        help="the pushed commit the fixtures are read from")
    parser.add_argument("--address", default="",
                        help="reuse an existing deployment")
    parser.add_argument("--scenarios", default="a,b,c,d,e")
    args = parser.parse_args()

    harden_provider()
    wanted = args.scenarios.split(",")

    say("# ClaimCourt live run")
    say()
    say("network   GenLayer Studionet, chain 61999")
    say("rpc       %s" % RPC)
    say("commit    %s" % args.commit)
    say()

    documents = {}
    for name in DOCUMENTS:
        url, digest, size = published(args.commit, name)
        documents[name] = (url, digest, size)
        say("document  %-34s %5d bytes  %s" % (name, size, digest))
    say()

    account, generated = signer()
    if generated:
        fund(account.address)
    chain = Chain(account)
    deploy_tx = ""
    if args.address:
        chain.bind(args.address)
    else:
        _address, deploy_tx = chain.deploy()
    say()

    results = []
    policies = []
    policy_url, policy_sha, _size = documents[POLICY_PROPERTY]

    say("## Policies")
    chain.write("register_policy",
                [policy_url, policy_sha, "small commercial property",
                 json.dumps(PROPERTY_DEFINITION)], "register_policy")
    property_policy = "pol-%d" % chain.read("get_stats")["policies"]
    policies.append(property_policy)
    record = chain.read("get_policy", [property_policy, 1])
    say("  %s version 1, policy hash %s"
        % (property_policy, record["policy_hash"]))

    theft_policy = ""
    crop_policy = ""
    if "c" in wanted:
        chain.write("register_policy",
                    [policy_url, policy_sha, "commercial theft",
                     json.dumps(THEFT_DEFINITION)], "register_policy")
        theft_policy = "pol-%d" % chain.read("get_stats")["policies"]
        policies.append(theft_policy)
        say("  %s version 1, theft conditions" % theft_policy)

    if "d" in wanted:
        crop_url, crop_sha, _size = documents[POLICY_CROP]
        chain.write("register_policy",
                    [crop_url, crop_sha, "parametric drought",
                     json.dumps(CROP_DEFINITION)], "register_policy")
        crop_policy = "pol-%d" % chain.read("get_stats")["policies"]
        policies.append(crop_policy)
        trigger = json.loads(chain.read("get_policy",
                                        [crop_policy, 1])["trigger"])
        say("  %s version 1, trigger %s %d %s in the window %s to %s"
            % (crop_policy, trigger["rule"], trigger["threshold"],
               trigger["unit"], trigger["window_start"],
               trigger["window_end"]))
    say()

    def adjudicate(policy_id, question, required, docs, incident, reference):
        chain.write("open_claim_challenge",
                    [policy_id, question, json.dumps(required), DEADLINE],
                    "open_claim_challenge")
        claim_id = "clm-%d" % chain.read("get_stats")["challenges"]
        chain.write("submit_claim",
                    [claim_id, reference, json.dumps(incident),
                     json.dumps(evidence_list(docs, documents))],
                    "submit_claim")
        submission_id = "sub-%d" % chain.read("get_stats")["submissions"]
        chain.write("resolve_submission", [submission_id],
                    "resolve_submission")
        return claim_id, submission_id

    def show_findings(submission_id):
        findings = chain.read("get_findings", [submission_id])
        for row in findings["conditions"]:
            say("    %-3s %-13s %s" % (row["ref"], row["finding"],
                                       row["quote"][:96]))
        for row in findings["exclusions"]:
            say("    %-3s %-13s %s" % (row["ref"], row["finding"],
                                       row["quote"][:96]))

    if "a" in wanted:
        say("## Scenario A - a claim that satisfies its policy")
        claim_id, submission_id = adjudicate(
            property_policy,
            "Does this claim satisfy the conditions of cover for the damage "
            "claimed, and does any exclusion apply?",
            ["incident_report", "invoice", "weather_record"],
            [("E1", "incident_report", STORM_REPORT),
             ("E2", "invoice", STORM_INVOICE),
             ("E3", "weather_record", STORM_OBSERVATION)],
            STORM_INCIDENT, "SYN-2041")
        record = chain.read("get_submission", [submission_id])
        verdict = chain.read("get_verdict", [submission_id])
        expect("verdict", record["verdict"], "COVERAGE_SUPPORTED")
        expect("status", record["status"], "RESOLVED")
        expect("evidence status", record["evidence_status"],
               "EVIDENCE_SUFFICIENT")
        expect("panel", record["panel_state"], "ASSESSED")
        expect("policy version verified",
               verdict["criteria"]["policy_version_verified"], True)
        expect("covered event supported",
               verdict["criteria"]["covered_event_supported"], True)
        expect("required conditions met",
               verdict["criteria"]["required_conditions_met"], True)
        expect("exclusion evidence found",
               verdict["criteria"]["exclusion_evidence_found"], False)
        expect("is_coverage_supported",
               chain.read("is_coverage_supported", [submission_id, AS_OF]),
               True)
        show_findings(submission_id)
        results.append(("A: claim satisfies the policy", claim_id,
                        submission_id, record["verdict"]))
        say()

    if "b" in wanted:
        say("## Scenario B - an exclusion the evidence shows")
        claim_id, submission_id = adjudicate(
            property_policy,
            "Does this claim satisfy the conditions of cover, and does the "
            "gradual deterioration exclusion apply?",
            ["incident_report", "assessor_report"],
            [("E1", "incident_report", STORM_REPORT),
             ("E2", "assessor_report", GRADUAL_REPORT)],
            GRADUAL_INCIDENT, "SYN-2052")
        record = chain.read("get_submission", [submission_id])
        expect_one_of("verdict", record["verdict"],
                      ["EXCLUSION_APPLIES", "COVERAGE_NOT_ESTABLISHED",
                       "INCONCLUSIVE"])
        expect("is_coverage_supported",
               chain.read("is_coverage_supported", [submission_id, AS_OF]),
               False)
        show_findings(submission_id)
        results.append(("B: exclusion evidenced", claim_id, submission_id,
                        record["verdict"]))
        say()

    if "c" in wanted:
        say("## Scenario C - a condition the evidence does not meet")
        claim_id, submission_id = adjudicate(
            theft_policy,
            "Was there forcible and violent entry, as the theft cover "
            "requires?",
            ["incident_report"],
            [("E1", "incident_report", NO_ENTRY_REPORT)],
            THEFT_INCIDENT, "SYN-2063")
        record = chain.read("get_submission", [submission_id])
        expect_one_of("verdict", record["verdict"],
                      ["COVERAGE_NOT_ESTABLISHED", "INCONCLUSIVE"])
        expect("is_coverage_supported",
               chain.read("is_coverage_supported", [submission_id, AS_OF]),
               False)
        show_findings(submission_id)
        results.append(("C: condition not met", claim_id, submission_id,
                        record["verdict"]))
        say()

    if "d" in wanted:
        say("## Scenario D - a parametric trigger, compared in code")
        claim_id, submission_id = adjudicate(
            crop_policy,
            "Was the insured rainfall trigger met for the named station and "
            "window?",
            ["holding_statement", "weather_record"],
            [("E1", "holding_statement", HOLDING_STATEMENT),
             ("E2", "weather_record", RAINFALL_RECORD)],
            CROP_INCIDENT, "SYN-3012")
        record = chain.read("get_submission", [submission_id])
        expect_one_of("verdict", record["verdict"],
                      ["COVERAGE_SUPPORTED", "INCONCLUSIVE"])
        say("    measurement read from the record: %d (trigger %s)"
            % (record["trigger_value"], record["trigger_state"]))
        if record["verdict"] == "COVERAGE_SUPPORTED":
            expect("trigger state", record["trigger_state"], "MET")
            expect("measurement", record["trigger_value"], 182)
        results.append(("D: parametric trigger", claim_id, submission_id,
                        record["verdict"]))
        say()

    if "e" in wanted:
        say("## Scenario E - evidence that addresses its reader")
        claim_id, submission_id = adjudicate(
            property_policy,
            "Does this claim satisfy the conditions of cover for the damage "
            "claimed, and does any exclusion apply?",
            ["incident_report", "invoice", "weather_record"],
            [("E1", "incident_report", DIRECTED_REPORT),
             ("E2", "invoice", STORM_INVOICE),
             ("E3", "weather_record", STORM_OBSERVATION)],
            STORM_INCIDENT, "SYN-2074")
        record = chain.read("get_submission", [submission_id])
        expect("verdict", record["verdict"], "INCONCLUSIVE")
        expect("status", record["status"], "RETRYABLE")
        say("    text addressed to the reader, counted in code: %d marker(s)"
            % record["directed_text_hits"])
        expect("is_coverage_supported",
               chain.read("is_coverage_supported", [submission_id, AS_OF]),
               False)
        expect("is_consumable",
               chain.read("is_consumable", [submission_id, AS_OF]), False)
        show_findings(submission_id)
        results.append(("E: evidence instructs its reader", claim_id,
                        submission_id, record["verdict"]))
        say()

    say("## The record")
    say()
    for policy_id in policies:
        say("    %s  %s" % (policy_id, json.dumps(
            chain.read("policy_record", [policy_id, 1]), sort_keys=True)))
    say("    stats   %s" % json.dumps(chain.read("get_stats"), sort_keys=True))
    say()

    say("## Summary")
    say()
    say("| Scenario | Challenge | Submission | Stored verdict |")
    say("|---|---|---|---|")
    for row in results:
        say("| %s | `%s` | `%s` | `%s` |" % row)
    say()
    if deploy_tx:
        status, execution, votes = chain.finality(deploy_tx)
        say("deployment %s, lifecycle %s, execution %s, %s"
            % (deploy_tx, status, execution, votes))
    say("contract   %s" % chain.address)
    say("explorer   %s/address/%s" % (EXPLORER, chain.address))

    PROOFS.mkdir(parents=True, exist_ok=True)
    (PROOFS / "live-run.log").write_text("\n".join(log_lines) + "\n",
                                         encoding="utf-8", newline="")
    ledger = {
        "network": "studionet", "chain_id": 61999, "rpc": RPC,
        "commit": args.commit, "contract": chain.address,
        "deployer": account.address, "deploy_tx": deploy_tx,
        "policies": policies,
        "transactions": [{"label": label, "tx": tx}
                         for label, tx in chain.transactions],
        "submissions": [{"scenario": row[0], "claim_id": row[1],
                         "submission_id": row[2], "verdict": row[3]}
                        for row in results],
        "documents": {name: {"url": documents[name][0],
                             "sha256": documents[name][1]}
                      for name in documents},
    }
    existing_path = PROOFS / "live.json"
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if existing.get("contract") == ledger["contract"]:
            seen = {row["tx"] for row in ledger["transactions"]}
            kept = [row for row in existing.get("transactions", [])
                    if row["tx"] not in seen]
            ledger["transactions"] = kept + ledger["transactions"]
            ids = {row["submission_id"] for row in ledger["submissions"]}
            ledger["submissions"] = [
                row for row in existing.get("submissions", [])
                if row["submission_id"] not in ids] + ledger["submissions"]
    existing_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="")
    say()
    say("written to docs/proofs/live-run.log and docs/proofs/live.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
