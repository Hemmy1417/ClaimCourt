"""Every verdict the contract can reach, derived from a mocked reading of
real fixture bytes. The panel's answer is mocked; the admission, grounding,
trigger comparison, precedence, storage and counter code under test is the
contract's own."""

import json

from conftest import (CROP_DEFINITION, CROP_EVIDENCE, CROP_INCIDENT,
                      DIRECTED_EVIDENCE, DIRECTED_REPORT, FRAUD_DEFINITION,
                      GRADUAL_EVIDENCE, GRADUAL_REPORT, HOLDING_STATEMENT,
                      NO_ENTRY_REPORT, POLICY_CROP, POLICY_PROPERTY,
                      RAINFALL_RECORD, STORM_INVOICE, STORM_REPORT,
                      THEFT_DEFINITION, THEFT_EVIDENCE, THEFT_INCIDENT,
                      TODAY_DATE, quote_from)


STORM_EVENT = quote_from(STORM_REPORT, "On the night of 2 to 3 March 2026 a")
STORM_NOTICE = quote_from(STORM_REPORT, "The insured became aware of the loss")
INVOICE_COST = quote_from(STORM_INVOICE, "Strip and replace damaged stockroom")
OCCUPIED = quote_from(STORM_REPORT, "The unit was in use up to and including")
GRADUAL = quote_from(GRADUAL_REPORT, "In my opinion this damage has developed")
NO_ENTRY = quote_from(NO_ENTRY_REPORT, "The side door was found closed but")
RAINFALL = quote_from(RAINFALL_RECORD, "Cumulative rainfall recorded: 182")
HOLDING = quote_from(HOLDING_STATEMENT, "This claim is made for the holding")
DIRECTED_EVENT = quote_from(DIRECTED_REPORT,
                            "On the night of 2 to 3 March 2026 a")


def _all_met():
    return [("C1", "MET", STORM_EVENT, "E1"),
            ("C2", "MET", STORM_NOTICE, "E1"),
            ("C3", "MET", INVOICE_COST, "E2")]


def _no_exclusions():
    return [("X1", "NOT_EVIDENCED", "", ""),
            ("X2", "NOT_EVIDENCED", "", "")]


def test_a_claim_that_meets_every_condition_is_supported(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"

    record = harness.contract.get_submission(submission_id)
    assert record["status"] == "RESOLVED"
    assert record["verdict"] == "COVERAGE_SUPPORTED"
    assert record["evidence_status"] == "EVIDENCE_SUFFICIENT"
    assert record["panel_state"] == "ASSESSED"
    assert record["policy_status"] == "EVIDENCE_REACHABLE"
    assert record["rounds_used"] == 1
    assert record["resolved_on"] == TODAY_DATE
    assert record["trigger_state"] == "NOT_DECLARED"
    assert record["fraud_finding"] == "NOT_ASKED"
    assert record["directed_text_hits"] == 0
    for item in record["evidence_refs"]:
        assert item["status"] == "EVIDENCE_REACHABLE"
        assert item["reason"] == ""
        assert item["byte_count"] > 0

    verdict = harness.contract.get_verdict(submission_id)
    assert verdict["verdict"] == "COVERAGE_SUPPORTED"
    assert verdict["coverage_conditions_met"] is True
    assert verdict["exclusion_applies"] is False
    assert verdict["evidence_status"] == "EVIDENCE_SUFFICIENT"
    assert verdict["criteria"] == {
        "policy_version_verified": True,
        "covered_event_supported": True,
        "required_conditions_met": True,
        "exclusion_evidence_found": False,
    }
    assert verdict["evidence_refs"] == ["E1", "E2"]
    assert verdict["bounded_reason"] == ""
    assert verdict["policy_hash"] == harness.contract.get_policy_hash(claim_id)

    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is True
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is True
    assert harness.contract.freshness(submission_id,
                                      TODAY_DATE) == "RELIABLE"
    assert harness.contract.get_evidence_status(
        submission_id) == "EVIDENCE_SUFFICIENT"
    record = harness.contract.policy_record(policy_id, 1)
    assert record["COVERAGE_SUPPORTED"] == 1
    assert record["total"] == 1
    assert harness.contract.get_stats()["resolved"] == 1


def test_a_condition_that_is_not_met_is_not_coverage(harness):
    policy_id = harness.register(THEFT_DEFINITION)
    claim_id = harness.open_challenge(policy_id, required=["incident_report"])
    harness.mock_docs(POLICY_PROPERTY, NO_ENTRY_REPORT)
    submission_id = harness.submit(claim_id, evidence=THEFT_EVIDENCE,
                                   incident=THEFT_INCIDENT,
                                   reference="SYN-2063")
    harness.mock_panel(harness.panel(
        [("C1", "MET", quote_from(NO_ENTRY_REPORT,
                                  "The insured attended the unit on the"),
          "E1"),
         ("C4", "NOT_MET", NO_ENTRY, "E1")],
        [("X1", "NOT_EVIDENCED", "", "")]))
    assert harness.resolve(submission_id) == "COVERAGE_NOT_ESTABLISHED"

    verdict = harness.contract.get_verdict(submission_id)
    assert verdict["coverage_conditions_met"] is False
    assert verdict["exclusion_applies"] is False
    assert verdict["criteria"]["required_conditions_met"] is False
    assert verdict["criteria"]["covered_event_supported"] is True
    assert "C4: not met" in verdict["bounded_reason"]
    # Not established is not fraud, and not a finding against the claimant.
    assert verdict["fraud_finding"] == "NOT_ASKED"
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is True


def test_an_evidenced_exclusion_outranks_the_conditions(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(
        policy_id, required=["incident_report", "invoice"])
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE,
                      GRADUAL_REPORT)
    submission_id = harness.submit(claim_id, evidence=GRADUAL_EVIDENCE)
    harness.mock_panel(harness.panel(
        _all_met(),
        [("X1", "EVIDENCED", GRADUAL, "E3"),
         ("X2", "NOT_EVIDENCED", "", "")]))
    # Every condition was met and the exclusion still decides it.
    assert harness.resolve(submission_id) == "EXCLUSION_APPLIES"

    verdict = harness.contract.get_verdict(submission_id)
    assert verdict["exclusion_applies"] is True
    assert verdict["criteria"]["exclusion_evidence_found"] is True
    assert verdict["criteria"]["required_conditions_met"] is True
    assert "X1: evidenced" in verdict["bounded_reason"]
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    findings = harness.contract.get_findings(submission_id)
    assert findings["exclusions"][0]["quote"] != ""
    assert findings["exclusions"][0]["evidence_id"] == "E3"


def test_an_unclear_condition_is_inconclusive_and_retryable(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        [("C1", "MET", STORM_EVENT, "E1"),
         ("C2", "UNCLEAR", "", ""),
         ("C3", "MET", INVOICE_COST, "E2")],
        _no_exclusions()))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"

    record = harness.contract.get_submission(submission_id)
    assert record["status"] == "RETRYABLE"
    assert record["rounds_used"] == 1
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is False
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    # Nothing was counted: an unsettled claim is not a policy's record.
    assert harness.contract.policy_record(policy_id, 1)["total"] == 0

    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_submission(
        submission_id) == "COVERAGE_SUPPORTED"
    record = harness.contract.get_submission(submission_id)
    assert record["status"] == "RESOLVED"
    assert record["rounds_used"] == 2
    assert harness.contract.get_receipt(submission_id, 1) != ""
    assert harness.contract.get_receipt(submission_id, 2) != ""
    assert harness.contract.policy_record(policy_id,
                                          1)["COVERAGE_SUPPORTED"] == 1


def test_contradictory_evidence_is_inconclusive(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE,
                      GRADUAL_REPORT)
    submission_id = harness.submit(claim_id, evidence=GRADUAL_EVIDENCE)
    harness.mock_panel(harness.panel(
        _all_met(), _no_exclusions(), contradiction=True,
        contradiction_quote=GRADUAL, contradiction_id="E3"))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_evidence_status(
        submission_id) == "EVIDENCE_CONTRADICTORY"
    assert harness.contract.get_submission(submission_id)["status"] \
        == "RETRYABLE"


def test_insufficient_evidence_is_never_a_coverage_verdict(ready):
    harness, _policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions(),
                                     sufficient=False))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_evidence_status(
        submission_id) == "EVIDENCE_INSUFFICIENT"


def test_a_missing_required_kind_is_never_adjudicated(harness):
    harness.register()
    policy_id = "pol-1"
    claim_id = harness.open_challenge(
        policy_id, required=["incident_report", "invoice"])
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT)
    # The invoice is committed but cannot be fetched, so a kind the
    # challenge requires is missing from the readable record.
    harness.mock_doc(STORM_INVOICE, status=404, body="not found")
    submission_id = harness.submit(claim_id)
    assert harness.resolve(submission_id) == "EVIDENCE_UNAVAILABLE"

    record = harness.contract.get_submission(submission_id)
    assert record["status"] == "RETRYABLE"
    assert record["evidence_status"] == "EVIDENCE_UNAVAILABLE"
    assert record["panel_state"] == "SKIPPED"
    assert record["evidence_refs"][1]["status"] == "EVIDENCE_UNAVAILABLE"
    assert record["evidence_refs"][1]["reason"] == "FETCH_FAILED"
    findings = harness.contract.get_findings(submission_id)
    assert [row["finding"] for row in findings["conditions"]] \
        == ["NOT_ASSESSED"] * 3
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False

    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_submission(
        submission_id) == "COVERAGE_SUPPORTED"


def test_a_substituted_document_is_not_the_document(ready):
    harness, _policy_id, claim_id = ready
    harness.clear()
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT)
    from conftest import doc_text
    harness.mock_doc(STORM_INVOICE,
                     body=doc_text(STORM_INVOICE) + "\nedited later\n")
    submission_id = harness.submit(claim_id)
    assert harness.resolve(submission_id) == "EVIDENCE_UNAVAILABLE"
    record = harness.contract.get_submission(submission_id)
    assert record["evidence_refs"][1]["reason"] == "HASH_MISMATCH"


def test_an_unreadable_policy_is_never_a_finding(ready):
    harness, _policy_id, claim_id = ready
    harness.clear()
    harness.mock_doc(POLICY_PROPERTY, status=503, body="unavailable")
    harness.mock_docs(STORM_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id)
    assert harness.resolve(submission_id) == "EVIDENCE_UNAVAILABLE"
    record = harness.contract.get_submission(submission_id)
    assert record["policy_status"] == "EVIDENCE_UNAVAILABLE"
    assert record["panel_state"] == "SKIPPED"
    verdict = harness.contract.get_verdict(submission_id)
    assert verdict["criteria"]["policy_version_verified"] is False


def test_evidence_that_addresses_its_reader_cannot_win_coverage(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, DIRECTED_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id, evidence=DIRECTED_EVIDENCE,
                                   reference="SYN-2074")
    harness.mock_panel(harness.panel(
        [("C1", "MET", DIRECTED_EVENT, "E1"),
         ("C2", "MET", quote_from(DIRECTED_REPORT,
                                  "The insured became aware of the loss"),
          "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        _no_exclusions()))
    # Every condition was read as met, and the verdict is still not
    # coverage: the evidence instructs whoever reads it.
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    record = harness.contract.get_submission(submission_id)
    assert record["directed_text_hits"] >= 3
    assert record["status"] == "RETRYABLE"
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    # The findings are kept: the claim was read, and what it says is on the
    # record even though it cannot settle.
    findings = harness.contract.get_findings(submission_id)
    assert findings["conditions"][0]["finding"] == "MET"


def test_a_parametric_trigger_is_compared_in_code(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"],
        question="Was the insured rainfall trigger met for the named "
                 "station and window?")
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3012")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"),
         ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": 182, "quote": RAINFALL,
                 "evidence_id": "E2"}))
    # 182 millimetres against a threshold of at most 220: the trigger fired.
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"
    record = harness.contract.get_submission(submission_id)
    assert record["trigger_state"] == "MET"
    assert record["trigger_value"] == 182


def test_a_trigger_that_did_not_fire_is_not_coverage(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3013")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"),
         ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": 486,
                 "quote": quote_from(RAINFALL_RECORD,
                                     "Cumulative rainfall recorded: 486"),
                 "evidence_id": "E2"}))
    # 486 against at most 220. Both conditions are met and the measurement
    # still decides it - the model never saw the threshold.
    assert harness.resolve(submission_id) == "COVERAGE_NOT_ESTABLISHED"
    record = harness.contract.get_submission(submission_id)
    assert record["trigger_state"] == "NOT_MET"
    assert record["trigger_value"] == 486
    verdict = harness.contract.get_verdict(submission_id)
    assert verdict["criteria"]["required_conditions_met"] is False
    assert verdict["criteria"]["covered_event_supported"] is False


def test_a_trigger_without_a_measurement_is_inconclusive(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3014")
    harness.mock_panel(harness.panel(
        [("C1", "MET", HOLDING, "E1"),
         ("C2", "MET", RAINFALL, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": False, "value": 0, "quote": "",
                 "evidence_id": ""}))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_submission(
        submission_id)["trigger_state"] == "UNREADABLE"


def test_fraud_is_only_found_where_the_policy_asks_and_the_words_are_there(
        harness):
    policy_id = harness.register(FRAUD_DEFINITION)
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        _all_met(), _no_exclusions(),
        fraud={"finding": "INDICATORS_FOUND", "quote": INVOICE_COST,
               "evidence_id": "E2", "basis": "synthetic test row"}))
    assert harness.resolve(submission_id) == "FRAUD_INDICATORS_FOUND"
    record = harness.contract.get_submission(submission_id)
    assert record["fraud_finding"] == "INDICATORS_FOUND"
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is True


def test_an_accusation_without_the_words_does_not_stand(harness):
    policy_id = harness.register(FRAUD_DEFINITION)
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        _all_met(), _no_exclusions(),
        fraud={"finding": "INDICATORS_FOUND",
               "quote": "the insured admitted inventing the whole loss",
               "evidence_id": "E2", "basis": "synthetic test row"}))
    # The quote is not in the document it names, so the accusation is
    # downgraded to uncertainty - never to its opposite, and never to a
    # finding of fraud.
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_submission(
        submission_id)["fraud_finding"] == "UNCLEAR"


def test_fraud_cannot_be_found_when_the_policy_never_asked(ready):
    harness, _policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        _all_met(), _no_exclusions(),
        fraud={"finding": "INDICATORS_FOUND", "quote": INVOICE_COST,
               "evidence_id": "E2", "basis": "synthetic test row"}))
    # The policy declares no fraud question, so an answer to one is not a
    # usable answer at all.
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    assert harness.contract.get_submission(
        submission_id)["panel_state"] == "INVALID"


def test_rounds_run_out_and_the_claim_settles_unsettled(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        [("C1", "UNCLEAR", "", ""), ("C2", "UNCLEAR", "", ""),
         ("C3", "UNCLEAR", "", "")], _no_exclusions()))
    assert harness.resolve(submission_id) == "INCONCLUSIVE"
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_submission(submission_id) == "INCONCLUSIVE"
    assert harness.contract.retry_submission(submission_id) == "INCONCLUSIVE"
    record = harness.contract.get_submission(submission_id)
    assert record["rounds_used"] == 3
    assert record["status"] == "RESOLVED"
    assert record["verdict"] == "INCONCLUSIVE"
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is False
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.retry_submission(submission_id)
    # An exhausted claim is counted, as the claim that could not be
    # settled: how often a policy's claims end that way is exactly the
    # signal the record exists to carry.
    assert harness.contract.get_stats()["resolved"] == 1
    record = harness.contract.policy_record(policy_id, 1)
    assert record["INCONCLUSIVE"] == 1
    assert record["COVERAGE_SUPPORTED"] == 0
    assert record["total"] == 1


def test_a_resolved_claim_is_terminal(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.resolve(submission_id)
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.resolve_submission(submission_id)
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.retry_submission(submission_id)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.cancel_submission(submission_id)
    assert harness.contract.policy_record(
        policy_id, 1)["COVERAGE_SUPPORTED"] == 1


def test_the_claimant_may_cancel_before_settlement(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the claimant"):
        harness.contract.cancel_submission(submission_id)
    harness.vm.sender = harness.claimant
    harness.contract.cancel_submission(submission_id)
    record = harness.contract.get_submission(submission_id)
    assert record["status"] == "CANCELLED"
    assert record["verdict"] == "CANCELLED"
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is False
    assert harness.contract.freshness(submission_id, TODAY_DATE) == "UNKNOWN"
    assert harness.contract.policy_record(policy_id, 1)["total"] == 0


def test_the_receipt_is_the_ratified_payload(ready):
    harness, _policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.resolve(submission_id)
    receipt = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert receipt["schema"] == "claimcourt/1"
    assert receipt["submission_id"] == submission_id
    assert receipt["claim_id"] == claim_id
    assert receipt["round"] == 1
    assert receipt["panel_state"] == "ASSESSED"
    assert receipt["policy_status"] == "EVIDENCE_REACHABLE"
    assert receipt["missing_required_kinds"] == []
    assert receipt["findings"]["conditions"][0]["finding"] == "MET"
    assert receipt["policy_hash"] == harness.contract.get_policy_hash(claim_id)
    assert receipt["evidence_digest"] == harness.contract.get_submission(
        submission_id)["evidence_digest"]


def test_a_verdict_goes_stale_after_its_window(harness):
    definition = json.loads(json.dumps(
        __import__("conftest").PROPERTY_DEFINITION))
    definition["review_window_days"] = 2
    policy_id = harness.register(definition)
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.resolve(submission_id)
    assert harness.contract.freshness(submission_id,
                                      "2026-10-19") == "RELIABLE"
    assert harness.contract.freshness(submission_id, "2026-10-20") == "STALE"
    assert harness.contract.is_coverage_supported(submission_id,
                                                  "2026-10-20") is False
    assert harness.contract.freshness(submission_id,
                                      "2026-10-01") == "UNKNOWN"
    assert harness.contract.freshness(submission_id, "not-a-date") == "UNKNOWN"
    assert policy_id == "pol-1"


def test_revoking_the_version_blocks_its_claims(ready):
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.resolve(submission_id)
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is True
    harness.vm.sender = harness.insurer
    harness.contract.revoke_policy_version(policy_id, 1)
    assert harness.contract.freshness(submission_id, TODAY_DATE) == "BLOCKED"
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is False
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    # The verdict is not rewritten: the record stays readable.
    assert harness.contract.get_submission(
        submission_id)["verdict"] == "COVERAGE_SUPPORTED"
    assert harness.contract.policy_record(
        policy_id, 1)["COVERAGE_SUPPORTED"] == 1
    assert claim_id == "clm-1"


def test_claim_outcome_is_one_read_for_a_consumer(ready):
    harness, _policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(_all_met(), _no_exclusions()))
    harness.resolve(submission_id)
    outcome = harness.contract.claim_outcome(submission_id, TODAY_DATE)
    assert outcome["verdict"] == "COVERAGE_SUPPORTED"
    assert outcome["coverage_supported"] is True
    assert outcome["consumable"] is True
    assert outcome["freshness"] == "RELIABLE"
    assert outcome["conditions_met"] == 3
    assert outcome["conditions_not_met"] == 0
    assert outcome["conditions_unclear"] == 0
    assert outcome["is_current_version"] is True
    assert outcome["evidence_status"] == "EVIDENCE_SUFFICIENT"
    assert outcome["policy_hash"] == harness.contract.get_policy_hash(claim_id)
