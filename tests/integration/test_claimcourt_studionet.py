"""Hosted Studionet integration: real deployment, real validators, real
documents, real consensus.

    gltest tests/integration -v -s --network studionet

Each behavioural test deploys its own contract, so the tests do not depend
on each other or on an order. These deployments are disposable; the
canonical deployment recorded in docs/DEPLOYMENT.md is made once by
scripts/live.py and is not replaced by a test run.

The documents are read from raw.githubusercontent.com at
CLAIMCOURT_FIXTURE_REF (a commit sha, or "main"). The suite checks that the
bytes published there match the local fixture before it binds them, so a
test can never pass against bytes a validator cannot fetch.
"""

import hashlib
import json
import os
import pathlib
import urllib.request

import pytest

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
# Relative to the contracts directory in gltest.config.yaml.
CONTRACT = "claimcourt.py"

REF = os.environ.get("CLAIMCOURT_FIXTURE_REF", "main")
RAW = "https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/%s/fixtures/%s"
RPC = "https://studio.genlayer.com/api"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

POLICY = "policy-household-v1.txt"
NOTICE_UNOCCUPIED = "notice-unoccupied.txt"
NOTICE_LATE = "notice-late-notification.txt"
NOTICE_DIRECTED = "notice-unoccupied-directed.txt"
MISSING = "notice-that-does-not-exist.txt"

GROUND_UNOCCUPIED = ("the insured address was left unoccupied for more than "
                     "sixty consecutive days immediately before the loss")
GROUND_LATE = ("because the notification was late the cover for this claim "
               "ended and no payment is due")
TODAY = "2026-10-17"

# The deployed contract carries the account it was deployed with, so a
# write needs only patience: a hosted round is slower than a local one.
WAIT = {"consensus_max_rotations": 3, "wait_interval": 5000,
        "wait_retries": 100}


def _published(name):
    """(url, sha256) for a document, proven to be fetchable and to match the
    committed fixture."""
    url = RAW % (REF, name)
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    digest = hashlib.sha256(body).hexdigest()
    local = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
    assert digest == local, (
        "%s at %s does not match the local fixture; push the fixtures first"
        % (name, REF))
    return url, digest


def _fund(address):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1,
                          "method": "sim_fundAccount",
                          "params": [address, 500000000000000000000]})
    request = urllib.request.Request(
        RPC, data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.fixture(scope="session")
def account():
    acct = get_default_account()
    _fund(acct.address)
    return acct


@pytest.fixture
def contract(account):
    factory = get_contract_factory(contract_file_path=CONTRACT)
    return factory.deploy(args=[], account=account,
                          consensus_max_rotations=3,
                          wait_interval=5000, wait_retries=100)


@pytest.fixture
def clause_set(contract, account):
    url, digest = _published(POLICY)
    receipt = contract.register_clause_set(
        args=["Household contents wording, synthetic edition 1", url, digest,
              365]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    record = contract.get_clause_set(args=["cs-1", 1]).call()
    assert record["policy_sha256"] == digest
    return "cs-1"


def _open(contract, account, clause_set_id, notice, refs, grounds,
          reference="SYN-LIVE"):
    url, digest = _published(notice)
    receipt = contract.open_review(
        args=[clause_set_id, url, digest, reference, refs,
              grounds]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    review_id = contract.notice_under_review(args=[digest]).call()
    assert review_id != ""
    return review_id


def test_deploy_and_public_surface(contract, clause_set):
    config = contract.get_config().call()
    assert config["schema"] == "claimcourt/1"
    assert "DENIAL_SUPPORTED" in config["verdicts"]
    assert config["max_grounds"] == 6
    record = contract.get_clause_set(args=[clause_set, 1]).call()
    assert record["version"] == 1
    assert record["revoked"] is False
    assert len(record["definition_hash"]) == 64
    assert contract.clause_set_head(args=[clause_set]).call() == 1
    assert contract.get_stats().call()["clause_sets"] == 1


def test_a_denial_that_stands(contract, account, clause_set):
    review_id = _open(contract, account, clause_set, NOTICE_UNOCCUPIED,
                      ["Clause 4.2"], [GROUND_UNOCCUPIED], "SYN-0041")
    receipt = contract.resolve_review(args=[review_id]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    # The receipt is not the proof: a round whose validators disagreed can
    # report success and store nothing. The stored state is the proof.
    review = contract.get_review(args=[review_id]).call()
    assert review["status"] == "RESOLVED"
    assert review["verdict"] == "DENIAL_SUPPORTED"
    assert review["policy_status"] == "EXAMINED"
    assert review["notice_status"] == "EXAMINED"
    assert review["panel_state"] == "READ"
    ground = contract.get_grounds(args=[review_id]).call()[0]
    assert ground["outcome"] == "SUPPORTED"
    # Every quote the panel returned was re-checked against the bytes each
    # node verified, so a stored quote really is in the document.
    assert len(ground["clause_quote"]) >= 12
    assert len(ground["notice_quote"]) >= 12
    assert contract.is_denial_supported(args=[review_id, TODAY]).call() is True
    assert contract.is_consumable(args=[review_id, TODAY]).call() is True
    assert contract.clause_record(
        args=[clause_set, 1, "Clause 4.2"]).call()["SUPPORTED"] == 1


def test_a_denial_the_clause_does_not_support(contract, account, clause_set):
    review_id = _open(contract, account, clause_set, NOTICE_LATE,
                      ["Clause 3.3"], [GROUND_LATE], "SYN-0052")
    receipt = contract.resolve_review(args=[review_id]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    review = contract.get_review(args=[review_id]).call()
    assert review["status"] == "RESOLVED"
    assert review["verdict"] == "DENIAL_UNSUPPORTED"
    assert contract.get_grounds(
        args=[review_id]).call()[0]["outcome"] == "UNSUPPORTED"
    assert contract.is_denial_supported(
        args=[review_id, TODAY]).call() is False
    assert contract.is_denial_unsupported(
        args=[review_id, TODAY]).call() is True


def test_a_notice_that_addresses_its_reader_is_not_upheld(contract, account,
                                                          clause_set):
    review_id = _open(contract, account, clause_set, NOTICE_DIRECTED,
                      ["Clause 4.2"], [GROUND_UNOCCUPIED], "SYN-0085")
    receipt = contract.resolve_review(args=[review_id]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    review = contract.get_review(args=[review_id]).call()
    # The notice tells its reader to uphold every ground. Code counted the
    # instruction, and the verdict cannot be an upholding.
    assert review["directed_text_hits"] >= 3
    assert review["verdict"] == "INCONCLUSIVE"
    assert review["status"] == "RETRYABLE"
    assert contract.is_denial_supported(
        args=[review_id, TODAY]).call() is False
    assert contract.is_consumable(args=[review_id, TODAY]).call() is False


def test_an_unfetchable_document_is_not_a_finding(contract, account,
                                                  clause_set):
    url = RAW % (REF, MISSING)
    receipt = contract.open_review(
        args=[clause_set, url, "d" * 64, "SYN-0099", ["Clause 4.2"],
              [GROUND_UNOCCUPIED]]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    review_id = contract.notice_under_review(args=["d" * 64]).call()
    receipt = contract.resolve_review(args=[review_id]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    review = contract.get_review(args=[review_id]).call()
    assert review["verdict"] == "RECORD_UNAVAILABLE"
    assert review["notice_status"] == "UNAVAILABLE"
    assert review["panel_state"] == "SKIPPED"
    assert review["status"] == "RETRYABLE"
    assert contract.is_consumable(args=[review_id, TODAY]).call() is False
    # The recovery path: the opener takes the review back, and the notice is
    # free to be reviewed again at a location that can be fetched.
    receipt = contract.withdraw_review(args=[review_id]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    assert contract.get_review(args=[review_id]).call()["status"] \
        == "WITHDRAWN"
    assert contract.notice_under_review(args=["d" * 64]).call() == ""
