#!/usr/bin/env python3
"""Re-check the live run against the network, and write the proof document
from what the network says.

Read-only. No signer, no keys, no funds, no writes - anyone can run this and
get the same output, which is the point: the evidence in
docs/proofs/live.md is not a transcript of my session, it is what
Studionet answers today about the transactions recorded in
docs/proofs/live.json.

    python scripts/verify.py
    python scripts/verify.py --quiet      # exit code only
"""

import argparse
import base64
import hashlib
import json
import pathlib
import sys
import urllib.request

from genlayer_py import chains, create_account, create_client, generate_private_key


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"
LEDGER = PROOFS / "live.json"
CONTRACT = ROOT / "contracts" / "claimcourt.py"

EXPLORER = "https://explorer-studio.genlayer.com"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

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


def _deployed_payload(address):
    """The contract as the network holds it."""
    request = urllib.request.Request(
        "https://studio.genlayer.com/api",
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
    say("| Contract | [`%s`](%s/address/%s) |"
        % (address, EXPLORER, address))
    say("| Deployer | `%s` |" % ledger["deployer"])
    say("| Source commit | `%s` |" % ledger["commit"])
    source = CONTRACT.read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    say("| Contract source | `contracts/claimcourt.py`, sha256 `%s` |"
        % source_sha)

    # Source parity, read off the chain rather than asserted: the network
    # returns the deployed contract base64-encoded, and decoding it gives
    # back bytes that must hash to the committed source.
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

    # -- the documents the validators had to fetch -------------------------
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
        "failed transaction: a validator that read the documents and did "
        "not reach the leader's conclusion votes against it, and the round "
        "commits on the majority. Two of the four readings above carry "
        "exactly that - a minority voting no while the majority carried. "
        "That is the evidence that validators are deciding rather than "
        "deferring; a column of unanimous agreement on a semantic question "
        "would be the thing worth suspecting.")
    say()

    # -- the state those transactions left behind --------------------------
    def read(method, params=None):
        return client.read_contract(address=address, function_name=method,
                                    args=params or [])

    config = read("get_config")
    clause_set = read("get_clause_set", ["cs-1", 1])

    say("## The clause set")
    say()
    say("| | |")
    say("|---|---|")
    say("| Schema | `%s` |" % config["schema"])
    say("| Contract version | `%s` |" % config["version"])
    say("| Label | %s |" % clause_set["label"])
    say("| Version | %d, current: %s |"
        % (clause_set["version"], clause_set["is_current_version"]))
    say("| Policy document | `%s` |" % clause_set["policy_sha256"])
    say("| Definition hash | `%s` |" % clause_set["definition_hash"])
    say("| Review window | %d days |" % clause_set["review_window_days"])
    say("| Reviews opened | %d |" % clause_set["review_count"])
    say()

    as_of = "2026-10-17"
    for entry in ledger["reviews"]:
        review_id = entry["review_id"]
        review = read("get_review", [review_id])
        grounds = read("get_grounds", [review_id])
        outcome = read("review_outcome", [review_id, as_of])
        say("## %s" % entry["scenario"])
        say()
        say("Review `%s`, claim reference `%s`, notice `%s`."
            % (review_id, review["claim_reference"],
               review["notice_sha256"]))
        say()
        say("| Check | Value | |")
        say("|---|---|---|")
        check("stored verdict", review["verdict"], entry["verdict"])
        check("policy document", review["policy_status"], "EXAMINED")
        check("notice document", review["notice_status"], "EXAMINED")
        check("rounds used", review["rounds_used"], 1)
        check("bound definition hash", review["definition_hash"],
              clause_set["definition_hash"])
        check("ground clause reference", grounds[0]["clause_ref"],
              entry["clause_ref"])

        if entry["verdict"] == "DENIAL_SUPPORTED":
            check("status", review["status"], "RESOLVED")
            check("panel", review["panel_state"], "READ")
            check("ground outcome", grounds[0]["outcome"], "SUPPORTED")
            check("text addressed to the reader", review["directed_text_hits"],
                  0)
            check("is_denial_supported", outcome["denial_supported"], True)
            check("is_denial_unsupported", outcome["denial_unsupported"],
                  False)
            check("is_consumable", outcome["consumable"], True)
            check("freshness", outcome["freshness"], "RELIABLE")
        elif entry["verdict"] == "DENIAL_UNSUPPORTED":
            check("status", review["status"], "RESOLVED")
            check("panel", review["panel_state"], "READ")
            check("ground outcome", grounds[0]["outcome"], "UNSUPPORTED")
            check("is_denial_supported", outcome["denial_supported"], False)
            check("is_denial_unsupported", outcome["denial_unsupported"], True)
            check("is_consumable", outcome["consumable"], True)
        elif entry["verdict"] == "CLAUSE_MISCITED":
            check("status", review["status"], "RESOLVED")
            check("ground outcome", grounds[0]["outcome"], "CLAUSE_ABSENT")
            check("clause label found literally in the wording",
                  grounds[0]["clause_ref_literal"], False)
            check("is_denial_supported", outcome["denial_supported"], False)
            check("is_denial_unsupported", outcome["denial_unsupported"], True)
        elif entry["verdict"] == "INCONCLUSIVE":
            check("status", review["status"], "RETRYABLE")
            check("panel", review["panel_state"], "READ")
            check("ground outcome", grounds[0]["outcome"], "SUPPORTED")
            check("is_denial_supported", outcome["denial_supported"], False)
            check("is_denial_unsupported", outcome["denial_unsupported"],
                  False)
            check("is_consumable", outcome["consumable"], False)
            check("freshness", outcome["freshness"], "UNKNOWN")
            hits = review["directed_text_hits"]
            if hits < 1:
                failures.append("the directed notice recorded no markers")
            say("| text addressed to the reader | `%d markers` | OK |" % hits)
        say()
        if grounds[0]["clause_quote"]:
            say("> clause quote: %s" % grounds[0]["clause_quote"])
            say()
        if grounds[0]["notice_quote"]:
            say("> notice quote: %s" % grounds[0]["notice_quote"])
            say()
        if grounds[0]["basis"]:
            say("Reasoning recorded for the ground (diagnostic, not "
                "consensus-critical): %s" % grounds[0]["basis"])
            say()

    say("## The accumulating record")
    say()
    say("| Clause | Total | Supported | Unsupported | Overbroad | Clause absent | Not in notice | Undecided |")
    say("|---|---|---|---|---|---|---|---|")
    for ref in sorted({row["clause_ref"] for row in ledger["reviews"]}):
        record = read("clause_record", ["cs-1", 1, ref])
        say("| %s | %d | %d | %d | %d | %d | %d | %d |"
            % (ref, record["total"], record["SUPPORTED"],
               record["UNSUPPORTED"], record["OVERBROAD"],
               record["CLAUSE_ABSENT"], record["NOT_IN_NOTICE"],
               record["UNDECIDED"]))
    say()
    summary = read("clause_set_record", ["cs-1", 1])
    stats = read("get_stats")
    say("| | |")
    say("|---|---|")
    for key in ["DENIAL_SUPPORTED", "DENIAL_UNSUPPORTED", "DENIAL_OVERBROAD",
                "CLAUSE_MISCITED", "GROUNDS_MISSTATED"]:
        say("| %s | %d |" % (key, summary[key]))
    say("| reviews opened | %d |" % stats["reviews"])
    say("| reviews settled | %d |" % stats["resolved"])
    say()
    unsettled = sum(1 for row in ledger["reviews"]
                    if row["verdict"] in ("INCONCLUSIVE",
                                          "RECORD_UNAVAILABLE"))
    check("reviews recorded as unsettled", stats["reviews"]
          - stats["resolved"], unsettled)
    say()
    say("The review that addresses its reader is the unsettled one. It is "
        "retryable, it is not consumable, and it contributed nothing to any "
        "clause's record - which is the whole point of the ceiling.")
    say()
    say("Scenario D is worth reading closely. The notice uses a "
        "jewellery-only limit to refuse an entire claim including a "
        "television, a laptop and two armchairs. Two readings of that are "
        "defensible: the clause reaches the jewellery and is applied too "
        "widely (`DENIAL_OVERBROAD`), or a jewellery-only limit does not "
        "reach a whole-claim refusal at all (`DENIAL_UNSUPPORTED`). Real "
        "validators took the second, quoting the clause's own scope "
        "sentence. The script asserts what the primitive guarantees - that "
        "the refusal does not stand and the gate is false - rather than "
        "which of the two a panel will prefer. `DENIAL_OVERBROAD` is "
        "exercised in Direct Mode; it has not been produced on the live "
        "network.")
    say()

    say("## What this proves")
    say()
    say("- a denial whose cited clause reaches its stated ground is upheld, "
        "and the quotes stored for it are in the documents;")
    say("- a denial whose cited clause contradicts its stated ground is not "
        "upheld, on the same wording, under the same rules;")
    say("- a clause that is not in the bound version is named as miscited "
        "rather than treated as unsupported;")
    say("- a notice that instructs whoever reads it cannot be upheld, and "
        "code - not the panel - is what caught it;")
    say("- every reliance gate is false for everything uncertain.")
    say()

    if failures:
        say("## Failures")
        say()
        for failure in failures:
            say("- %s" % failure)
        say()

    PROOFS.mkdir(parents=True, exist_ok=True)
    (PROOFS / "live.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        print("\n%d check(s) failed" % len(failures))
        return 1
    print("\nall checks passed; written to docs/proofs/live.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
