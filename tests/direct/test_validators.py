"""The validator, run against forged leader results.

`run_validator` replays the contract's own validator closure, so these are
not simulations of a gate - they are the gate. Each test stages what one
node would have seen, hands the validator a leader result, and asserts the
vote. True-controls are included so a False is never just a broken setup.
"""

import copy
import json

import pytest

from conftest import (CROP_DEFINITION, CROP_EVIDENCE, CROP_INCIDENT,
                      FRAUD_DEFINITION, HOLDING_STATEMENT, POLICY_CROP,
                      POLICY_PROPERTY, RAINFALL_RECORD, STORM_INVOICE,
                      STORM_REPORT, quote_from)


STORM_EVENT = quote_from(STORM_REPORT, "On the night of 2 to 3 March 2026 a")
STORM_EVENT_ALT = quote_from(STORM_REPORT, "A section of the roof covering")
STORM_NOTICE = quote_from(STORM_REPORT, "The insured became aware of the loss")
INVOICE_COST = quote_from(STORM_INVOICE, "Strip and replace damaged stockroom")
INVOICE_ALT = quote_from(STORM_INVOICE, "The damage we attended was")
RAINFALL = quote_from(RAINFALL_RECORD, "Cumulative rainfall recorded: 182")
HOLDING = quote_from(HOLDING_STATEMENT, "This claim is made for the holding")


def _panel(harness, c1="MET", c2="MET", c3="MET", exclusion="NOT_EVIDENCED"):
    return harness.panel(
        [("C1", c1, STORM_EVENT if c1 != "UNCLEAR" else "",
          "E1" if c1 != "UNCLEAR" else ""),
         ("C2", c2, STORM_NOTICE if c2 != "UNCLEAR" else "",
          "E1" if c2 != "UNCLEAR" else ""),
         ("C3", c3, INVOICE_COST if c3 != "UNCLEAR" else "",
          "E2" if c3 != "UNCLEAR" else "")],
        [("X1", exclusion, INVOICE_ALT if exclusion == "EVIDENCED" else "",
          "E2" if exclusion == "EVIDENCED" else ""),
         ("X2", "NOT_EVIDENCED", "", "")])


@pytest.fixture
def adjudicated(ready):
    """One claim adjudicated honestly, with the payload it produced."""
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(_panel(harness))
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    return harness, submission_id, payload


def _vote(harness, payload):
    return harness.vm.run_validator(leader_result=json.dumps(payload))


def test_an_honest_leader_is_agreed_with(adjudicated):
    harness, _submission_id, payload = adjudicated
    assert harness.vm.run_validator() is True
    assert _vote(harness, payload) is True


def test_different_prose_is_not_disagreement(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][0]["basis"] = \
        "the report describes a storm on the night the damage was found"
    forged["findings"]["evidence"]["basis"] = "the papers hang together"
    assert _vote(harness, forged) is True


def test_a_different_but_grounded_quote_is_not_disagreement(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][0]["quote"] = STORM_EVENT_ALT
    forged["findings"]["conditions"][2]["quote"] = INVOICE_ALT
    assert _vote(harness, forged) is True


@pytest.mark.parametrize("index,finding", [
    (0, "NOT_MET"), (1, "NOT_MET"), (2, "UNCLEAR"), (0, "NOT_ASSESSED"),
])
def test_a_forged_condition_finding_is_rejected(adjudicated, index, finding):
    """Each of these changes the outcome the payload carries, and the
    outcome is what the round agrees on."""
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][index]["finding"] = finding
    assert _vote(harness, forged) is False


def test_the_outcome_is_what_must_agree_not_the_label_behind_it(adjudicated):
    """Two honest nodes reading the same documents can label a condition
    differently and still reach the same verdict. Requiring every label to
    match would split the round over nothing - and did, on the live network,
    before this was the rule.

    What must still match is the verdict and the four criteria, and a
    payload whose outcome does not follow from its own findings is refused
    by the gate before any of this (see test_gate_units.py).
    """
    harness, _submission_id, payload = adjudicated
    import sys
    module = sys.modules[type(harness.contract).__module__]

    # This node read every condition as met and the claim as covered. A
    # leader that reached the same verdict by a different route agrees.
    assert payload["verdict"] == "COVERAGE_SUPPORTED"
    reworded = copy.deepcopy(payload)
    reworded["findings"]["conditions"][1]["basis"] = "the dates are stated"
    reworded["findings"]["conditions"][1]["quote"] = STORM_EVENT_ALT
    assert _vote(harness, reworded) is True

    # A verdict this node did not reach is refused, however well-formed.
    for verdict in ["COVERAGE_NOT_ESTABLISHED", "INCONCLUSIVE",
                    "EXCLUSION_APPLIES"]:
        forged = copy.deepcopy(payload)
        forged["verdict"] = verdict
        assert _vote(harness, forged) is False

    # So is a criterion this node did not find.
    for field in ["policy_version_verified", "covered_event_supported",
                  "required_conditions_met", "exclusion_evidence_found"]:
        forged = copy.deepcopy(payload)
        forged["criteria"][field] = not forged["criteria"][field]
        assert _vote(harness, forged) is False
    assert module is not None


def test_a_forged_exclusion_is_rejected(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["exclusions"][0]["finding"] = "EVIDENCED"
    forged["findings"]["exclusions"][0]["quote"] = INVOICE_ALT
    forged["findings"]["exclusions"][0]["evidence_id"] = "E2"
    # The quote is real, so the payload passes the grounding check and is
    # still rejected: this node read the exclusion as not evidenced.
    assert _vote(harness, forged) is False


def test_an_invented_quote_is_rejected_even_when_the_finding_matches(
        adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][0]["quote"] = \
        "the insured has proved every element of this claim beyond doubt"
    assert _vote(harness, forged) is False


def test_a_quote_from_the_wrong_document_is_rejected(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][2]["quote"] = STORM_EVENT
    forged["findings"]["conditions"][2]["evidence_id"] = "E2"
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("submission_id", "sub-999"),
    ("claim_id", "clm-999"),
    ("round", 2),
    ("round", 0),
    ("policy_hash", "f" * 64),
    ("policy_sha256", "a" * 64),
    ("evidence_digest", "b" * 64),
    ("policy_version", 2),
    ("schema", "claimcourt/2"),
])
def test_a_rebound_payload_is_rejected(adjudicated, field, value):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged[field] = value
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("policy_status", "EVIDENCE_UNAVAILABLE"),
    ("policy_reason", "HASH_MISMATCH"),
    ("panel_state", "SKIPPED"),
    ("panel_state", "INVALID"),
    ("panel_state", "AGREED"),
    ("directed_text_hits", 4),
    ("trigger_state", "MET"),
    ("trigger_state", "NOT_DECLARED_YET"),
])
def test_a_forged_decision_field_is_rejected(adjudicated, field, value):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged[field] = value
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("sufficient", False),
    ("contradiction", True),
])
def test_a_forged_evidence_judgement_is_rejected(adjudicated, field, value):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["evidence"][field] = value
    if field == "contradiction":
        forged["findings"]["evidence"]["quote"] = INVOICE_ALT
        forged["findings"]["evidence"]["evidence_id"] = "E2"
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("status", "EVIDENCE_UNAVAILABLE"),
    ("reason", "TOO_LARGE"),
    ("kind", "photograph"),
    ("evidence_id", "E9"),
    ("byte_count", 10),
])
def test_a_forged_document_row_is_rejected(adjudicated, field, value):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["rows"][0][field] = value
    assert _vote(harness, forged) is False


def test_a_forged_missing_kinds_list_is_rejected(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["missing_required_kinds"] = ["invoice"]
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("finding", 1),
    ("finding", True),
    ("finding", "MET_ISH"),
    ("quote", 7),
    ("evidence_id", False),
    ("ref", "C9"),
])
def test_a_wrongly_typed_row_field_is_rejected(adjudicated, field, value):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"][0][field] = value
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("section", [
    "schema", "submission_id", "round", "policy_hash", "rows", "findings",
    "panel_state", "policy_status", "missing_required_kinds",
    "directed_text_hits", "trigger_state",
])
def test_a_missing_payload_field_is_rejected(adjudicated, section):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    del forged[section]
    assert _vote(harness, forged) is False


def test_an_added_or_dropped_row_is_rejected(adjudicated):
    harness, _submission_id, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["conditions"].append(
        dict(forged["findings"]["conditions"][0]))
    assert _vote(harness, forged) is False
    forged = copy.deepcopy(payload)
    forged["rows"] = forged["rows"][:1]
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("raw", [
    "", "   ", "not json at all", "{", "[]", '{"schema":"claimcourt/1"}',
])
def test_an_unreadable_leader_result_is_rejected(adjudicated, raw):
    harness, _submission_id, _payload = adjudicated
    assert harness.vm.run_validator(leader_result=raw) is False


def test_claiming_a_document_was_read_when_it_cannot_be_fetched(adjudicated):
    harness, _submission_id, payload = adjudicated
    assert _vote(harness, payload) is True
    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT)
    harness.mock_doc(STORM_INVOICE, status=500, body="error")
    assert _vote(harness, payload) is False


def test_claiming_a_document_is_unavailable_when_it_can_be_read(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT)
    harness.mock_doc(STORM_INVOICE, status=404, body="missing")
    submission_id = harness.submit(claim_id)
    assert harness.resolve(submission_id) == "EVIDENCE_UNAVAILABLE"
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert harness.vm.run_validator() is True
    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    harness.mock_panel(_panel(harness))
    assert _vote(harness, payload) is False


def test_a_forged_trigger_measurement_is_rejected(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3012")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"), ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": 486,
                 "quote": quote_from(RAINFALL_RECORD,
                                     "Cumulative rainfall recorded: 486"),
                 "evidence_id": "E2"}))
    assert harness.resolve(submission_id) == "COVERAGE_NOT_ESTABLISHED"
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert harness.vm.run_validator() is True
    # A leader that reports the other window's figure, with that figure's
    # own real quote, still loses: this node read 486.
    forged = copy.deepcopy(payload)
    forged["findings"]["trigger"]["value"] = 182
    forged["findings"]["trigger"]["quote"] = RAINFALL
    forged["trigger_state"] = "MET"
    assert _vote(harness, forged) is False


def test_a_forged_fraud_finding_is_rejected(harness):
    policy_id = harness.register(FRAUD_DEFINITION)
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        [("C1", "MET", STORM_EVENT, "E1"),
         ("C2", "MET", STORM_NOTICE, "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        [("X1", "NOT_EVIDENCED", "", ""), ("X2", "NOT_EVIDENCED", "", "")],
        fraud={"finding": "NO_INDICATORS", "quote": "", "evidence_id": "",
               "basis": "nothing in the papers suggests it"}))
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert harness.vm.run_validator() is True
    forged = copy.deepcopy(payload)
    forged["findings"]["fraud"]["finding"] = "INDICATORS_FOUND"
    forged["findings"]["fraud"]["quote"] = INVOICE_ALT
    forged["findings"]["fraud"]["evidence_id"] = "E2"
    # A real quote, a well-formed payload, and an accusation this node did
    # not make.
    assert _vote(harness, forged) is False
    assert policy_id == "pol-1"


def test_a_transient_leader_failure_is_agreed_with_only_when_shared(
        adjudicated):
    harness, _submission_id, _payload = adjudicated
    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    # No panel is reachable for this node either.
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is True


def test_a_transient_claim_is_rejected_when_this_node_succeeds(adjudicated):
    harness, _submission_id, _payload = adjudicated
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is False


def test_a_panel_failure_is_never_agreed_with(adjudicated):
    harness, _submission_id, _payload = adjudicated
    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    assert harness.vm.run_validator(
        leader_error=Exception("[PANEL] the ratified payload failed the "
                               "gate")) is False


def test_an_unexplained_leader_failure_is_rejected(adjudicated):
    harness, _submission_id, _payload = adjudicated
    assert harness.vm.run_validator(leader_error=Exception("boom")) is False
    assert harness.vm.run_validator(
        leader_error=Exception("[EXPECTED] no such submission")) is False
