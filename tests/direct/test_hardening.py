"""Hostile panel output, through the real pipeline.

Every case asserts two things: the verdict fails closed, and the stored
state stays honest - no finding, no counter, no consumability.
"""

import json

import pytest

from conftest import (CROP_DEFINITION, CROP_EVIDENCE, CROP_INCIDENT,
                      FRAUD_DEFINITION, HOLDING_STATEMENT, POLICY_CROP,
                      POLICY_PROPERTY, RAINFALL_RECORD, STORM_INVOICE,
                      STORM_OBSERVATION, STORM_REPORT, TODAY_DATE, quote_from)


STORM_EVENT = quote_from(STORM_REPORT, "On the night of 2 to 3 March 2026 a")
STORM_NOTICE = quote_from(STORM_REPORT, "The insured became aware of the loss")
INVOICE_COST = quote_from(STORM_INVOICE, "Strip and replace damaged stockroom")
RAINFALL = quote_from(RAINFALL_RECORD, "Cumulative rainfall recorded: 182")
HOLDING = quote_from(HOLDING_STATEMENT, "This claim is made for the holding")


def _good(harness):
    return harness.panel(
        [("C1", "MET", STORM_EVENT, "E1"),
         ("C2", "MET", STORM_NOTICE, "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        [("X1", "NOT_EVIDENCED", "", ""),
         ("X2", "NOT_EVIDENCED", "", "")])


def _resolve_with(ready, raw):
    harness, _policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(raw)
    return submission_id, harness.resolve(submission_id)


def _assert_unread(harness, submission_id, policy_id="pol-1"):
    record = harness.contract.get_submission(submission_id)
    assert record["verdict"] == "INCONCLUSIVE"
    assert record["status"] == "RETRYABLE"
    assert record["panel_state"] == "INVALID"
    assert record["policy_status"] == "EVIDENCE_REACHABLE"
    assert record["evidence_status"] == "EVIDENCE_INSUFFICIENT"
    findings = harness.contract.get_findings(submission_id)
    for row in findings["conditions"]:
        assert row["finding"] == "NOT_ASSESSED"
        assert row["quote"] == ""
    for row in findings["exclusions"]:
        assert row["finding"] == "NOT_ASSESSED"
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    assert harness.contract.policy_record(policy_id, 1)["total"] == 0


@pytest.mark.parametrize("raw,label", [
    ("", "empty answer"),
    ("   ", "blank answer"),
    ("the claim looks fine to me", "prose with no json"),
    ("{", "truncated json"),
    ('{"conditions":', "cut off mid key"),
    ('["conditions"]', "a list where an object is required"),
    ('{"rows":[]}', "the wrong key"),
    ('{"conditions":{}}', "an object where a list is required"),
    ('{"conditions":[],"exclusions":[],"evidence":{}}', "no rows at all"),
])
def test_an_unusable_panel_answer_fails_closed(ready, raw, label):
    harness, _policy_id, _claim_id = ready
    submission_id, verdict = _resolve_with(ready, raw)
    assert verdict == "INCONCLUSIVE", label
    _assert_unread(harness, submission_id)


def test_a_row_count_that_does_not_match_the_policy_fails_closed(ready):
    harness, _policy_id, _claim_id = ready
    short = harness.panel([("C1", "MET", STORM_EVENT, "E1")],
                          [("X1", "NOT_EVIDENCED", "", "")])
    submission_id, verdict = _resolve_with(ready, short)
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)


def test_rows_out_of_order_fail_closed(ready):
    harness, _policy_id, _claim_id = ready
    swapped = harness.panel(
        [("C2", "MET", STORM_NOTICE, "E1"),
         ("C1", "MET", STORM_EVENT, "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        [("X1", "NOT_EVIDENCED", "", ""), ("X2", "NOT_EVIDENCED", "", "")])
    submission_id, verdict = _resolve_with(ready, swapped)
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)


@pytest.mark.parametrize("mutation,label", [
    ('"finding": 1', "a number where a finding is required"),
    ('"finding": true', "a boolean where a finding is required"),
    ('"finding": "SUPPORTED"', "a finding word from another protocol"),
    ('"finding": "NOT_ASSESSED"', "claiming not assessed on a read round"),
    ('"finding": null', "a null finding"),
    ('"quote": 42', "a number where a quote is required"),
    ('"evidence_id": 7', "a number where a document id is required"),
    ('"ref": "C9"', "a reference the policy does not have"),
])
def test_a_wrongly_typed_condition_row_fails_closed(ready, mutation, label):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    key, value = mutation.split(":", 1)
    answer["conditions"][0][json.loads(key)] = json.loads(value)
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE", label
    _assert_unread(harness, submission_id)


@pytest.mark.parametrize("field,value", [
    ("sufficient", 1),
    ("sufficient", "true"),
    ("sufficient", None),
    ("contradiction", 0),
    ("contradiction", "false"),
])
def test_a_wrongly_typed_evidence_block_fails_closed(ready, field, value):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["evidence"][field] = value
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)


@pytest.mark.parametrize("missing", ["conditions", "exclusions", "evidence"])
def test_a_missing_section_fails_closed(ready, missing):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    del answer[missing]
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)


def test_a_fenced_answer_is_recovered(ready):
    harness, _policy_id, _claim_id = ready
    submission_id, verdict = _resolve_with(
        ready, "```json\n" + _good(harness) + "\n```")
    assert verdict == "COVERAGE_SUPPORTED"
    assert harness.contract.get_submission(
        submission_id)["panel_state"] == "ASSESSED"


def test_an_answer_wrapped_in_prose_is_recovered(ready):
    harness, _policy_id, _claim_id = ready
    _submission_id, verdict = _resolve_with(
        ready, "Here is my assessment.\n" + _good(harness) + "\nI hope that "
        "helps.")
    assert verdict == "COVERAGE_SUPPORTED"


def test_a_lowercase_finding_is_normalised(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["finding"] = " met "
    _submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "COVERAGE_SUPPORTED"


def test_an_unrequested_extra_field_is_ignored(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["confidence"] = "high"
    answer["note"] = "an extra section nobody asked for"
    _submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "COVERAGE_SUPPORTED"


def test_a_fractional_number_anywhere_in_the_answer_fails_closed(ready):
    harness, _policy_id, _claim_id = ready
    # The runtime cannot carry a float through its calldata, so an answer
    # containing one arrives as nothing at all. The contract must read that
    # as an unusable answer rather than as any kind of finding.
    answer = json.loads(_good(harness))
    answer["conditions"][0]["confidence"] = 0.92
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)


def test_an_invented_quote_cannot_establish_a_condition(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["quote"] = \
        "the insured has proved every element of this claim beyond doubt"
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    # The panel said the condition was met. The words are not in the
    # document it named, so the finding does not stand - and it is
    # downgraded to uncertainty, never to its opposite.
    assert verdict == "INCONCLUSIVE"
    findings = harness.contract.get_findings(submission_id)
    assert findings["conditions"][0]["finding"] == "UNCLEAR"
    assert findings["conditions"][0]["quote"] == ""
    assert findings["conditions"][1]["finding"] == "MET"


def test_an_invented_quote_cannot_refuse_a_condition_either(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][1]["finding"] = "NOT_MET"
    answer["conditions"][1]["quote"] = "the insured never told us anything"
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    assert harness.contract.get_findings(
        submission_id)["conditions"][1]["finding"] == "UNCLEAR"


def test_a_quote_from_the_wrong_document_does_not_ground(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    # The words are real, and they are in E1, not in the invoice.
    answer["conditions"][2]["quote"] = STORM_EVENT
    answer["conditions"][2]["evidence_id"] = "E2"
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    assert harness.contract.get_findings(
        submission_id)["conditions"][2]["finding"] == "UNCLEAR"


def test_an_ungrounded_exclusion_does_not_decide_the_claim(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["exclusions"][0]["finding"] = "EVIDENCED"
    answer["exclusions"][0]["quote"] = "the damage was obviously old"
    answer["exclusions"][0]["evidence_id"] = "E1"
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    # An exclusion that cannot be quoted is not an exclusion that applies.
    assert verdict == "INCONCLUSIVE"
    assert harness.contract.get_findings(
        submission_id)["exclusions"][0]["finding"] == "UNCLEAR"
    assert harness.contract.get_verdict(
        submission_id)["exclusion_applies"] is False


def test_an_ungrounded_contradiction_is_dropped(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["evidence"]["contradiction"] = True
    answer["evidence"]["quote"] = "the two reports cannot both be right"
    answer["evidence"]["evidence_id"] = "E1"
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "COVERAGE_SUPPORTED"
    assert harness.contract.get_evidence_status(
        submission_id) == "EVIDENCE_SUFFICIENT"


def test_a_quote_too_short_to_mean_anything_does_not_ground(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["quote"] = "storm"
    _submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"


def test_whitespace_and_case_do_not_break_grounding(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["quote"] = \
        "  ON THE NIGHT of 2 to 3   March 2026 a storm passed  "
    _submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "COVERAGE_SUPPORTED"


def test_oversized_quotes_and_reasoning_are_bounded(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["conditions"][0]["quote"] = quote_from(
        STORM_REPORT, "On the night of 2 to 3 March 2026 a", 1200)
    answer["conditions"][0]["basis"] = "b" * 900
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "COVERAGE_SUPPORTED"
    row = harness.contract.get_findings(submission_id)["conditions"][0]
    assert len(row["basis"]) == 240
    assert 230 <= len(row["quote"]) <= 240


def test_a_trigger_value_the_panel_invents_is_dropped(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3015")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"), ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": 11,
                 "quote": "cumulative rainfall recorded: 11 millimetres",
                 "evidence_id": "E2"}))
    # 11 would have fired the trigger. The record does not say it, so the
    # measurement does not stand and nothing is paid on it.
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    record = harness.contract.get_submission(submission_id)
    assert record["trigger_state"] == "UNREADABLE"
    assert record["trigger_value"] == 0


@pytest.mark.parametrize("value", [-1, True, "182"])
def test_a_wrongly_typed_trigger_value_fails_closed(harness, value):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3016")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"), ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": value, "quote": RAINFALL,
                 "evidence_id": "E2"}))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_submission(
        submission_id)["panel_state"] == "INVALID"
    assert policy_id == "pol-1"


@pytest.mark.parametrize("finding", ["GUILTY", "yes", "FOUND", True, 1])
def test_an_unknown_fraud_finding_fails_closed(harness, finding):
    policy_id = harness.register(FRAUD_DEFINITION)
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT,
                      STORM_INVOICE, STORM_OBSERVATION)
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        [("C1", "MET", STORM_EVENT, "E1"),
         ("C2", "MET", STORM_NOTICE, "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        [("X1", "NOT_EVIDENCED", "", ""), ("X2", "NOT_EVIDENCED", "", "")],
        fraud={"finding": finding, "quote": "", "evidence_id": "",
               "basis": ""}))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    record = harness.contract.get_submission(submission_id)
    assert record["panel_state"] == "INVALID"
    assert record["fraud_finding"] == "UNCLEAR"
    assert policy_id == "pol-1"


def test_a_fraud_answer_where_none_was_asked_fails_closed(ready):
    harness, _policy_id, _claim_id = ready
    answer = json.loads(_good(harness))
    answer["fraud"] = {"finding": "NO_INDICATORS", "quote": "",
                       "evidence_id": "", "basis": "nothing seen"}
    submission_id, verdict = _resolve_with(ready, json.dumps(answer))
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, submission_id)
