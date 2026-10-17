#!/usr/bin/env python3
"""Live evidence driver for hosted Studionet.

Deploys `contracts/claimcourt.py` as it stands, then runs the three
scenarios that matter - a denial that stands, a denial that does not, and a
recovery path - against real validators reading real documents. Every
transaction hash, every stored result and every assertion is printed, and
the run is written to docs/proofs/live.md.

    python scripts/live.py --commit <sha>          deploy and run everything
    python scripts/live.py --commit <sha> --address 0x...   reuse a deployment

The fixtures must already be pushed: the documents are read from
raw.githubusercontent.com at the commit given, so the bytes the validators
fetch are pinned and cannot change under the review.

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

from genlayer_py import chains, create_client, create_account, generate_private_key
from genlayer_py.types import TransactionStatus


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "claimcourt.py"
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"

RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
RAW = "https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/%s/fixtures/%s"

POLICY = "policy-household-v1.txt"
NOTICE_UNOCCUPIED = "notice-unoccupied.txt"
NOTICE_LATE = "notice-late-notification.txt"
NOTICE_FLOOD = "notice-flood-clause.txt"
NOTICE_JEWELLERY = "notice-jewellery-limit.txt"
NOTICE_DIRECTED = "notice-unoccupied-directed.txt"

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

TRANSIENT_MARKERS = ["BAD_RECORD_MAC", "RemoteDisconnected", "ConnectionReset",
                     "Connection aborted", "timed out", "<!DOCTYPE html>",
                     "502", "503", "504", "EOF occurred"]

log_lines = []


def say(text=""):
    print(text, flush=True)
    log_lines.append(text)


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


# -- documents ---------------------------------------------------------------

def published_sha(commit, name):
    """The sha256 of the bytes a validator will actually fetch, read from
    the pinned raw location - not the sha256 of the local file. If they
    differ, the fixture is not pushed, and the review would bind bytes
    nobody can fetch."""
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


def revert_reason(receipt):
    try:
        leader = receipt.get("consensus_data", {}).get("leader_receipt")
        if isinstance(leader, list) and leader:
            return str(leader[0].get("result", {}).get("payload", ""))[:300]
    except Exception:
        pass
    return ""


def consensus_summary(receipt):
    """Agreement as the receipt actually records it. An idle validator is not
    a disagreeing one, and collapsing the two would overstate dissent as
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
        say("contract %s" % address)
        say("explorer %s/address/%s" % (EXPLORER, address))
        return address, _hex(tx_hash), receipt

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
        say("  %-28s tx %s  %s  %s"
            % (label, _hex(tx_hash), result, consensus_summary(receipt)))
        self.transactions.append((label, _hex(tx_hash)))
        if result.upper().endswith("ERROR"):
            say("  revert: %s" % revert_reason(receipt))
            raise SystemExit("%s failed on chain" % label)
        return _hex(tx_hash), receipt

    def read(self, method, args=None):
        return self.client.read_contract(address=self.address,
                                         function_name=method,
                                         args=args or [])

    def finality(self, tx_hash):
        tx = self.client.get_transaction(transaction_hash=tx_hash)
        return lifecycle(tx), execution_result(tx), consensus_summary(tx)


def _hex(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


# -- the run -----------------------------------------------------------------

GROUND_UNOCCUPIED = ("the insured address was left unoccupied for more than "
                     "sixty consecutive days immediately before the loss")
GROUND_LATE = ("because the notification was late the cover for this claim "
               "ended and no payment is due")
GROUND_FLOOD = "the damage was caused by flood or rising groundwater"
GROUND_JEWELLERY = ("because the claim exceeds the jewellery limit we are "
                    "declining the claim in its entirety")


def expect_one_of(label, actual, allowed):
    ok = actual in allowed
    say("    %-44s %s  (%s)" % (label, "OK" if ok else "WRONG", actual))
    if not ok:
        raise SystemExit("%s: expected one of %r, got %r"
                         % (label, allowed, actual))


def expect(label, actual, wanted):
    ok = actual == wanted
    say("    %-44s %s  (%s)" % (label, "OK" if ok else "WRONG", actual))
    if not ok:
        raise SystemExit("%s: expected %r, got %r" % (label, wanted, actual))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True,
                        help="the pushed commit the fixtures are read from")
    parser.add_argument("--address", default="",
                        help="reuse an existing deployment")
    parser.add_argument("--scenarios", default="a,b,c")
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
    for name in [POLICY, NOTICE_UNOCCUPIED, NOTICE_LATE, NOTICE_FLOOD,
                 NOTICE_JEWELLERY, NOTICE_DIRECTED]:
        url, digest, size = published_sha(args.commit, name)
        documents[name] = (url, digest)
        say("document  %-34s %d bytes  %s" % (name, size, digest))
    say()

    account, generated = signer()
    if generated:
        fund(account.address)
    chain = Chain(account)
    deploy_tx = ""
    if args.address:
        chain.bind(args.address)
    else:
        _address, deploy_tx, _receipt = chain.deploy()
    say()

    policy_url, policy_sha = documents[POLICY]
    clause_set_id = "cs-1"
    if args.address and int(chain.read("clause_set_head", ["cs-1"]) or 0) >= 1:
        say("reusing clause set cs-1 on the existing deployment")
    else:
        say("registering the clause set")
        chain.write("register_clause_set",
                    ["Household contents wording, synthetic edition 1",
                     policy_url, policy_sha, 365], "register_clause_set")
    record = chain.read("get_clause_set", [clause_set_id, 1])
    say("  clause set %s version 1, definition hash %s"
        % (clause_set_id, record["definition_hash"]))
    say()

    results = []

    if "a" in wanted:
        say("## Scenario A - a denial that stands")
        url, digest = documents[NOTICE_UNOCCUPIED]
        open_tx, _ = chain.write(
            "open_review", [clause_set_id, url, digest, "SYN-0041",
                            ["Clause 4.2"], [GROUND_UNOCCUPIED]],
            "open_review")
        review_id = chain.read("notice_under_review", [digest])
        resolve_tx, _ = chain.write("resolve_review", [review_id],
                                    "resolve_review")
        review = chain.read("get_review", [review_id])
        grounds = chain.read("get_grounds", [review_id])
        expect("verdict", review["verdict"], "DENIAL_SUPPORTED")
        expect("status", review["status"], "RESOLVED")
        expect("policy document", review["policy_status"], "EXAMINED")
        expect("notice document", review["notice_status"], "EXAMINED")
        expect("panel", review["panel_state"], "READ")
        expect("ground outcome", grounds[0]["outcome"], "SUPPORTED")
        expect("is_denial_supported", chain.read(
            "is_denial_supported", [review_id, "2026-10-17"]), True)
        expect("is_consumable", chain.read(
            "is_consumable", [review_id, "2026-10-17"]), True)
        say("    clause quote: %s" % grounds[0]["clause_quote"][:120])
        say("    notice quote: %s" % grounds[0]["notice_quote"][:120])
        results.append(("A: denial stands", review_id, open_tx, resolve_tx,
                        review["verdict"]))
        say()

    if "b" in wanted:
        say("## Scenario B - a denial the clause does not support")
        url, digest = documents[NOTICE_LATE]
        open_tx, _ = chain.write(
            "open_review", [clause_set_id, url, digest, "SYN-0052",
                            ["Clause 3.3"], [GROUND_LATE]], "open_review")
        review_id = chain.read("notice_under_review", [digest])
        resolve_tx, _ = chain.write("resolve_review", [review_id],
                                    "resolve_review")
        review = chain.read("get_review", [review_id])
        grounds = chain.read("get_grounds", [review_id])
        expect("verdict", review["verdict"], "DENIAL_UNSUPPORTED")
        expect("ground outcome", grounds[0]["outcome"], "UNSUPPORTED")
        expect("is_denial_supported", chain.read(
            "is_denial_supported", [review_id, "2026-10-17"]), False)
        expect("is_denial_unsupported", chain.read(
            "is_denial_unsupported", [review_id, "2026-10-17"]), True)
        say("    clause quote: %s" % grounds[0]["clause_quote"][:120])
        results.append(("B: denial unsupported", review_id, open_tx,
                        resolve_tx, review["verdict"]))
        say()

    if "c" in wanted:
        say("## Scenario C - a clause that is not in the wording, and a "
            "notice that addresses its reader")
        url, digest = documents[NOTICE_FLOOD]
        chain.write("open_review",
                    [clause_set_id, url, digest, "SYN-0074", ["Clause 9.4"],
                     [GROUND_FLOOD]], "open_review")
        review_id = chain.read("notice_under_review", [digest])
        miscite_tx, _ = chain.write("resolve_review", [review_id],
                                    "resolve_review")
        review = chain.read("get_review", [review_id])
        expect("verdict", review["verdict"], "CLAUSE_MISCITED")
        expect("ground outcome",
               chain.read("get_grounds", [review_id])[0]["outcome"],
               "CLAUSE_ABSENT")
        results.append(("C1: clause miscited", review_id, "", miscite_tx,
                        review["verdict"]))

        url, digest = documents[NOTICE_DIRECTED]
        chain.write("open_review",
                    [clause_set_id, url, digest, "SYN-0085", ["Clause 4.2"],
                     [GROUND_UNOCCUPIED]], "open_review")
        directed_id = chain.read("notice_under_review", [digest])
        directed_tx, _ = chain.write("resolve_review", [directed_id],
                                     "resolve_review")
        review = chain.read("get_review", [directed_id])
        expect("verdict", review["verdict"], "INCONCLUSIVE")
        expect("status", review["status"], "RETRYABLE")
        say("    directed text found by code: %d marker(s)"
            % review["directed_text_hits"])
        expect("is_consumable", chain.read(
            "is_consumable", [directed_id, "2026-10-17"]), False)
        results.append(("C2: notice addresses reader", directed_id, "",
                        directed_tx, review["verdict"]))

        withdraw_id = chain.read("notice_under_review", [digest])
        say()
        say("## The accumulating record")
        for ref in ["Clause 4.2", "Clause 3.3", "Clause 9.4"]:
            say("    %-12s %s" % (ref, json.dumps(
                chain.read("clause_record", [clause_set_id, 1, ref]),
                sort_keys=True)))
        say("    clause set  %s" % json.dumps(
            chain.read("clause_set_record", [clause_set_id, 1]),
            sort_keys=True))
        say("    stats       %s" % json.dumps(chain.read("get_stats"),
                                              sort_keys=True))
        say("    (review %s stays retryable: nothing was decided)"
            % withdraw_id)
        say()

    if "d" in wanted:
        say("## Scenario D - a clause applied past its own stated scope")
        url, digest = documents[NOTICE_JEWELLERY]
        open_tx, _ = chain.write(
            "open_review", [clause_set_id, url, digest, "SYN-0063",
                            ["Clause 5.4"], [GROUND_JEWELLERY]],
            "open_review")
        review_id = chain.read("notice_under_review", [digest])
        resolve_tx, _ = chain.write("resolve_review", [review_id],
                                    "resolve_review")
        review = chain.read("get_review", [review_id])
        grounds = chain.read("get_grounds", [review_id])
        # Two readings of this notice are defensible, and the contract is
        # designed to keep them apart rather than merge them: the clause
        # reaches the jewellery items but is applied to the whole claim
        # (OVERBROAD), or a jewellery-only limit does not reach a
        # whole-claim refusal at all (UNSUPPORTED). What must hold either
        # way is that the refusal does not stand. Asserting one of the two
        # would be asserting a model's taste, not the primitive's
        # guarantee.
        expect_one_of("verdict", review["verdict"],
                      ["DENIAL_OVERBROAD", "DENIAL_UNSUPPORTED"])
        expect_one_of("ground outcome", grounds[0]["outcome"],
                      ["OVERBROAD", "UNSUPPORTED"])
        # Overbroad is neither an upholding nor a plain lack of support:
        # both convenience gates are false and the consumer must read the
        # verdict itself.
        expect("is_denial_supported", chain.read(
            "is_denial_supported", [review_id, "2026-10-17"]), False)
        expect("is_denial_unsupported", chain.read(
            "is_denial_unsupported", [review_id, "2026-10-17"]), False)
        expect("is_consumable", chain.read(
            "is_consumable", [review_id, "2026-10-17"]), True)
        say("    clause quote: %s" % grounds[0]["clause_quote"][:160])
        say("    notice quote: %s" % grounds[0]["notice_quote"][:160])
        results.append(("D: clause applied too widely", review_id, open_tx,
                        resolve_tx, review["verdict"]))
        say()

    say("## Summary")
    say()
    say("| Scenario | Review | Open tx | Resolve tx | Stored verdict |")
    say("|---|---|---|---|---|")
    for row in results:
        say("| %s | `%s` | `%s` | `%s` | `%s` |" % row)
    say()
    if deploy_tx:
        status, votes = chain.finality(deploy_tx)
        say("deployment %s, lifecycle %s %s" % (deploy_tx, status, votes))
    say("contract   %s" % chain.address)
    say("explorer   %s/address/%s" % (EXPLORER, chain.address))

    PROOFS.mkdir(parents=True, exist_ok=True)
    (PROOFS / "live-run.log").write_text("\n".join(log_lines) + "\n",
                                         encoding="utf-8")
    # The ledger is what makes the run checkable by someone else: every
    # transaction it produced, the contract, and the commit the documents
    # were pinned at. scripts/verify.py reads it back off the network and
    # writes docs/proofs/live.md from what it finds there.
    ledger = {
        "network": "studionet", "chain_id": 61999, "rpc": RPC,
        "commit": args.commit, "contract": chain.address,
        "deployer": account.address, "deploy_tx": deploy_tx,
        "transactions": [{"label": label, "tx": tx}
                         for label, tx in chain.transactions],
        "reviews": [{"scenario": row[0], "review_id": row[1],
                     "verdict": row[4]} for row in results],
        "documents": {name: {"url": url, "sha256": digest}
                      for name, (url, digest) in documents.items()},
    }
    (PROOFS / "live.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    say()
    say("written to docs/proofs/live-run.log and docs/proofs/live.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
