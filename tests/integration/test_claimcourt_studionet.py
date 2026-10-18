"""Hosted Studionet integration: real deployment, real validators, real
documents, real consensus.

    CLAIMCOURT_FIXTURE_REF=<sha> gltest tests/integration -v -s --network studionet

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

POLICY_PROPERTY = "policy-property-v1.txt"
STORM_REPORT = "incident-report-storm.txt"
STORM_INVOICE = "repair-invoice-storm.txt"
NO_ENTRY_REPORT = "incident-report-no-forced-entry.txt"
DIRECTED_REPORT = "incident-report-directed.txt"
MISSING = "document-that-does-not-exist.txt"

DEADLINE = "2027-06-30"
AS_OF = "2026-10-18"

# The deployed contract carries the account it was deployed with, so a write
# needs only patience: a hosted round is slower than a local one.
WAIT = {"consensus_max_rotations": 3, "wait_interval": 5000,
        "wait_retries": 100}

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
    "exclusions": [],
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

THEFT_INCIDENT = {
    "incident_summary": "Stock and a laptop were found missing from the "
                        "unit on the morning of 29 July 2026.",
    "incident_date": "2026-07-29",
    "incident_location_reference": "SYN-UNIT-12",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}


def _published(name):
    """(url, sha256) for a document, proven fetchable and identical to the
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
    return factory.deploy(args=[], account=account, **WAIT)


def _register(contract, definition=PROPERTY_DEFINITION,
              coverage_type="small commercial property"):
    url, digest = _published(POLICY_PROPERTY)
    receipt = contract.register_policy(
        args=[url, digest, coverage_type, json.dumps(definition)]
    ).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    return "pol-1", digest


def _challenge(contract, policy_id, question, required):
    receipt = contract.open_claim_challenge(
        args=[policy_id, question, json.dumps(required), DEADLINE]
    ).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    return "clm-1"


def _submit(contract, claim_id, documents, incident, reference):
    evidence = []
    for evidence_id, kind, name in documents:
        if name == MISSING:
            evidence.append({"evidence_id": evidence_id, "kind": kind,
                             "url": RAW % (REF, MISSING),
                             "sha256": "d" * 64})
            continue
        url, digest = _published(name)
        evidence.append({"evidence_id": evidence_id, "kind": kind,
                         "url": url, "sha256": digest})
    receipt = contract.submit_claim(
        args=[claim_id, reference, json.dumps(incident),
              json.dumps(evidence)]).transact(**WAIT)
    assert tx_execution_succeeded(receipt)
    return "sub-1"


def test_deploy_and_public_surface(contract):
    config = contract.get_config().call()
    assert config["schema"] == "claimcourt/1"
    assert "COVERAGE_SUPPORTED" in config["verdicts"]
    assert config["max_evidence"] == 6

    policy_id, digest = _register(contract)
    policy = contract.get_policy(args=[policy_id, 1]).call()
    assert policy["policy_sha256"] == digest
    assert len(policy["policy_hash"]) == 64
    assert [c["ref"] for c in policy["coverage_conditions"]] == ["C1", "C2",
                                                                "C3"]

    claim_id = _challenge(
        contract, policy_id,
        "Does this claim satisfy the conditions of cover for the damage "
        "claimed, and does any exclusion apply?",
        ["incident_report", "invoice"])
    claim = contract.get_claim(args=[claim_id]).call()
    assert claim["policy_version"] == 1
    assert claim["required_evidence"] == ["incident_report", "invoice"]
    assert claim["status"] == "OPEN"
    assert contract.get_policy_hash(args=[claim_id]).call() \
        == policy["policy_hash"]
    assert contract.get_stats().call()["challenges"] == 1


def test_a_claim_that_satisfies_its_policy(contract):
    policy_id, _digest = _register(contract)
    claim_id = _challenge(
        contract, policy_id,
        "Does this claim satisfy the conditions of cover for the damage "
        "claimed, and does any exclusion apply?",
        ["incident_report", "invoice"])
    submission_id = _submit(
        contract, claim_id,
        [("E1", "incident_report", STORM_REPORT),
         ("E2", "invoice", STORM_INVOICE)], STORM_INCIDENT, "SYN-2041")

    receipt = contract.resolve_submission(args=[submission_id]).transact(
        **WAIT)
    assert tx_execution_succeeded(receipt)
    # The receipt is not the proof: a round whose validators disagreed can
    # report success and store nothing. The stored state is the proof.
    record = contract.get_submission(args=[submission_id]).call()
    assert record["status"] == "RESOLVED"
    assert record["verdict"] == "COVERAGE_SUPPORTED"
    assert record["evidence_status"] == "EVIDENCE_SUFFICIENT"
    assert record["panel_state"] == "ASSESSED"
    assert record["policy_status"] == "EVIDENCE_REACHABLE"
    for item in record["evidence_refs"]:
        assert item["status"] == "EVIDENCE_REACHABLE"
        assert item["byte_count"] > 0

    verdict = contract.get_verdict(args=[submission_id]).call()
    assert verdict["criteria"] == {
        "policy_version_verified": True,
        "covered_event_supported": True,
        "required_conditions_met": True,
        "exclusion_evidence_found": False,
    }
    # Every finding that counts carries words from the documents, re-checked
    # by each validator against the bytes it verified itself.
    findings = contract.get_findings(args=[submission_id]).call()
    for row in findings["conditions"]:
        assert row["finding"] == "MET"
        assert len(row["quote"]) >= 12
        assert row["evidence_id"] in ("E1", "E2")
    assert contract.is_coverage_supported(
        args=[submission_id, AS_OF]).call() is True
    assert contract.policy_record(
        args=[policy_id, 1]).call()["COVERAGE_SUPPORTED"] == 1


def test_a_condition_the_evidence_does_not_meet(contract):
    policy_id, _digest = _register(contract, THEFT_DEFINITION,
                                   "commercial theft")
    claim_id = _challenge(
        contract, policy_id,
        "Was there forcible and violent entry, as the theft cover requires?",
        ["incident_report"])
    submission_id = _submit(
        contract, claim_id, [("E1", "incident_report", NO_ENTRY_REPORT)],
        THEFT_INCIDENT, "SYN-2063")

    receipt = contract.resolve_submission(args=[submission_id]).transact(
        **WAIT)
    assert tx_execution_succeeded(receipt)
    record = contract.get_submission(args=[submission_id]).call()
    # Either the panel settles it against the claim or it cannot settle it.
    # What must hold is that the claim does not become covered, and that a
    # claim not established is never called fraud.
    assert record["verdict"] in ("COVERAGE_NOT_ESTABLISHED", "INCONCLUSIVE")
    assert record["fraud_finding"] == "NOT_ASKED"
    assert contract.is_coverage_supported(
        args=[submission_id, AS_OF]).call() is False
    if record["verdict"] == "COVERAGE_NOT_ESTABLISHED":
        verdict = contract.get_verdict(args=[submission_id]).call()
        assert verdict["criteria"]["required_conditions_met"] is False
        assert contract.is_consumable(args=[submission_id, AS_OF]).call() \
            is True


def test_evidence_that_addresses_its_reader_cannot_win_coverage(contract):
    policy_id, _digest = _register(contract)
    claim_id = _challenge(
        contract, policy_id,
        "Does this claim satisfy the conditions of cover for the damage "
        "claimed, and does any exclusion apply?",
        ["incident_report", "invoice"])
    submission_id = _submit(
        contract, claim_id,
        [("E1", "incident_report", DIRECTED_REPORT),
         ("E2", "invoice", STORM_INVOICE)], STORM_INCIDENT, "SYN-2074")

    receipt = contract.resolve_submission(args=[submission_id]).transact(
        **WAIT)
    assert tx_execution_succeeded(receipt)
    record = contract.get_submission(args=[submission_id]).call()
    # The report tells its reader to approve the claim. Code counted the
    # instruction, and the claim cannot become covered on that reading.
    assert record["directed_text_hits"] >= 3
    assert record["verdict"] == "INCONCLUSIVE"
    assert record["status"] == "RETRYABLE"
    assert contract.is_coverage_supported(
        args=[submission_id, AS_OF]).call() is False
    assert contract.is_consumable(args=[submission_id, AS_OF]).call() is False
    assert policy_id == "pol-1"


def test_an_unfetchable_required_document_is_not_a_finding(contract):
    policy_id, _digest = _register(contract)
    claim_id = _challenge(
        contract, policy_id,
        "Does this claim satisfy the conditions of cover for the damage "
        "claimed, and does any exclusion apply?",
        ["incident_report", "invoice"])
    submission_id = _submit(
        contract, claim_id,
        [("E1", "incident_report", STORM_REPORT),
         ("E2", "invoice", MISSING)], STORM_INCIDENT, "SYN-2099")

    receipt = contract.resolve_submission(args=[submission_id]).transact(
        **WAIT)
    assert tx_execution_succeeded(receipt)
    record = contract.get_submission(args=[submission_id]).call()
    assert record["verdict"] == "EVIDENCE_UNAVAILABLE"
    assert record["evidence_status"] == "EVIDENCE_UNAVAILABLE"
    assert record["panel_state"] == "SKIPPED"
    assert record["status"] == "RETRYABLE"
    assert record["evidence_refs"][1]["status"] == "EVIDENCE_UNAVAILABLE"
    assert record["evidence_refs"][1]["reason"] == "FETCH_FAILED"
    # Nothing was assessed, so nothing was found against anyone.
    findings = contract.get_findings(args=[submission_id]).call()
    for row in findings["conditions"]:
        assert row["finding"] == "NOT_ASSESSED"
    assert contract.is_consumable(args=[submission_id, AS_OF]).call() is False

    # The recovery path: the claimant withdraws the claim rather than
    # leaving it unsettled.
    receipt = contract.cancel_submission(args=[submission_id]).transact(
        **WAIT)
    assert tx_execution_succeeded(receipt)
    record = contract.get_submission(args=[submission_id]).call()
    assert record["status"] == "CANCELLED"
    assert record["verdict"] == "CANCELLED"
    assert contract.is_consumable(args=[submission_id, AS_OF]).call() is False
    assert policy_id == "pol-1"
