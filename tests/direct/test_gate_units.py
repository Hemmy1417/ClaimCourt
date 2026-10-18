"""The gate, exercised directly.

Several of the contract's rules are second lines of defence: in a normal
round the validator's field-by-field comparison catches the same attack
first, so removing them changes no end-to-end result. They still matter -
the ratified payload is parsed once more after consensus, where no
validator is left to compare against - and a rule nothing exercises is a
rule nothing protects.

These tests call `_parse_payload`, `_derive_verdict`, `_criteria`,
`_evidence_status` and `_record` with staged inputs, so each rule is
responsible for its own failure.
"""

import copy
import json
import sys

import pytest

from conftest import STORM_INVOICE, STORM_REPORT, TODAY_DATE, quote_from


STORM_EVENT = quote_from(STORM_REPORT, "On the night of 2 to 3 March 2026 a")
STORM_NOTICE = quote_from(STORM_REPORT, "The insured became aware of the loss")
INVOICE_COST = quote_from(STORM_INVOICE, "Strip and replace damaged stockroom")


@pytest.fixture
def adjudicated(ready):
    """A settled claim, plus the context and payload the round used."""
    harness, policy_id, claim_id = ready
    submission_id = harness.submit(claim_id)
    harness.mock_panel(harness.panel(
        [("C1", "MET", STORM_EVENT, "E1"),
         ("C2", "MET", STORM_NOTICE, "E1"),
         ("C3", "MET", INVOICE_COST, "E2")],
        [("X1", "NOT_EVIDENCED", "", ""), ("X2", "NOT_EVIDENCED", "", "")]))
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"
    record = harness.contract.submissions.get(submission_id)
    context = harness.contract._context(record)
    # _context is built for the NEXT round; the payload is from the last one.
    context["round"] = int(record.rounds_used)
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    return harness, policy_id, submission_id, context, payload


@pytest.fixture
def module(adjudicated):
    """The contract's own module, as Direct Mode loaded it. Derived from the
    deployed class rather than named, so the mutation sweep - which loads a
    patched copy under its own name - exercises these tests too."""
    return sys.modules[type(adjudicated[0].contract).__module__]



def _restate(module, context, payload):
    """Keep a staged payload internally consistent.

    The gate re-derives the verdict and the criteria from the findings, so a
    payload whose findings were changed must restate its own outcome.
    Without this, every staged payload below would be rejected for the wrong
    reason and would prove nothing about the rule it is testing.
    """
    payload["criteria"] = module._criteria(context, payload)
    payload["verdict"] = module._derive_verdict(context, payload)
    return payload


def test_the_honest_payload_passes_the_gate(module, adjudicated):
    """The control. Without it, every rejection below could be a staging
    error rather than a rule doing its job."""
    _harness, _policy, _submission, context, payload = adjudicated
    parsed = module._parse_payload(payload, context, None, None)
    assert parsed is not None
    assert module._derive_verdict(context, parsed) == "COVERAGE_SUPPORTED"
    assert module._evidence_status(parsed) == "EVIDENCE_SUFFICIENT"
    assert module._criteria(context, parsed) == {
        "policy_version_verified": True,
        "covered_event_supported": True,
        "required_conditions_met": True,
        "exclusion_evidence_found": False,
    }


def test_a_substantive_finding_without_its_words_is_refused(module,
                                                            adjudicated):
    """MET and NOT_MET both count against someone. Neither may arrive
    without the quote it rests on."""
    _harness, _policy, _submission, context, payload = adjudicated
    for finding in ["MET", "NOT_MET"]:
        forged = copy.deepcopy(payload)
        forged["findings"]["conditions"][0]["finding"] = finding
        forged["findings"]["conditions"][0]["quote"] = ""
        forged["findings"]["conditions"][0]["evidence_id"] = ""
        assert module._parse_payload(_restate(module, context, forged),
                                     context, None, None) is None

    # The uncertain form may carry no quote, which is the whole point of it.
    unclear = copy.deepcopy(payload)
    unclear["findings"]["conditions"][0]["finding"] = "UNCLEAR"
    unclear["findings"]["conditions"][0]["quote"] = ""
    unclear["findings"]["conditions"][0]["evidence_id"] = ""
    parsed = module._parse_payload(_restate(module, context, unclear),
                                   context, None, None)
    assert parsed is not None
    assert module._derive_verdict(context, parsed) == "INCONCLUSIVE"


def test_an_evidenced_exclusion_without_its_words_is_refused(module,
                                                             adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["exclusions"][0]["finding"] = "EVIDENCED"
    forged["findings"]["exclusions"][0]["quote"] = ""
    assert module._parse_payload(forged, context, None, None) is None


def test_an_accusation_without_its_words_is_refused(harness):
    """Staged on a policy that does ask a fraud question: on one that does
    not, the answer is refused for a different reason entirely."""
    import sys

    from conftest import (FRAUD_DEFINITION, POLICY_PROPERTY, STORM_INVOICE,
                      STORM_OBSERVATION, STORM_REPORT)

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
        fraud={"finding": "NO_INDICATORS", "quote": "", "evidence_id": "",
               "basis": "nothing in the papers suggests it"}))
    assert harness.resolve(submission_id) == "COVERAGE_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get(submission_id)
    context = harness.contract._context(record)
    context["round"] = int(record.rounds_used)
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert module._parse_payload(payload, context, None, None) is not None

    forged = copy.deepcopy(payload)
    forged["findings"]["fraud"]["finding"] = "INDICATORS_FOUND"
    forged["findings"]["fraud"]["quote"] = ""
    assert module._parse_payload(_restate(module, context, forged),
                                 context, None, None) is None

    # ... and only an accusation may carry a quote at all.
    forged = copy.deepcopy(payload)
    forged["findings"]["fraud"]["quote"] = INVOICE_COST
    forged["findings"]["fraud"]["evidence_id"] = "E2"
    assert module._parse_payload(_restate(module, context, forged),
                                 context, None, None) is None


def _unassessed(payload):
    """The shape a round that did not assess is allowed to have."""
    unread = copy.deepcopy(payload)
    for row in unread["findings"]["conditions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    for row in unread["findings"]["exclusions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    unread["findings"]["evidence"].update(
        {"sufficient": False, "contradiction": False, "quote": "",
         "evidence_id": ""})
    return unread


def test_a_round_that_did_not_assess_cannot_carry_a_finding(module,
                                                            adjudicated):
    """When the panel did not answer, every row has one permitted shape.

    Each case leaves exactly one branch standing between the payload and
    acceptance, so the rejection is attributable to that branch."""
    _harness, _policy, _submission, context, payload = adjudicated
    for state in ["INVALID", "SKIPPED"]:
        # a condition carrying a finding, everything else in the unread shape
        forged = _unassessed(payload)
        forged["panel_state"] = state
        forged["findings"]["conditions"][0].update(
            {"finding": "MET",
             "quote": payload["findings"]["conditions"][0]["quote"],
             "evidence_id": payload["findings"]["conditions"][0][
                 "evidence_id"]})
        assert module._parse_payload(_restate(module, context, forged),
                                     context, None, None) is None

        # an exclusion carrying a finding, everything else in the unread shape
        forged = _unassessed(payload)
        forged["panel_state"] = state
        forged["findings"]["exclusions"][0]["finding"] = "NOT_EVIDENCED"
        assert module._parse_payload(_restate(module, context, forged),
                                     context, None, None) is None

        # the evidence block claiming a judgement nobody made
        forged = _unassessed(payload)
        forged["panel_state"] = state
        forged["findings"]["evidence"]["sufficient"] = True
        assert module._parse_payload(_restate(module, context, forged),
                                     context, None, None) is None

    unread = copy.deepcopy(payload)
    unread["panel_state"] = "INVALID"
    for row in unread["findings"]["conditions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    for row in unread["findings"]["exclusions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    unread["findings"]["evidence"].update(
        {"sufficient": False, "contradiction": False, "quote": "",
         "evidence_id": ""})
    parsed = module._parse_payload(_restate(module, context, unread),
                                   context, None, None)
    assert parsed is not None, "the permitted shape must still be accepted"
    assert module._derive_verdict(context, parsed) == "INCONCLUSIVE"
    assert module._evidence_status(parsed) == "EVIDENCE_INSUFFICIENT"


def test_a_panel_state_that_contradicts_the_record_is_refused(module,
                                                              adjudicated):
    """A reading cannot have happened on documents nobody could examine, and
    a round where everything was readable cannot report the panel as
    skipped."""
    _harness, _policy, _submission, context, payload = adjudicated
    unreadable = copy.deepcopy(payload)
    unreadable["policy_status"] = "EVIDENCE_UNAVAILABLE"
    unreadable["policy_reason"] = "FETCH_FAILED"
    assert unreadable["panel_state"] == "ASSESSED"
    assert module._parse_payload(_restate(module, context, unreadable),
                                 context, None, None) is None

    missing = copy.deepcopy(payload)
    missing["rows"][1]["status"] = "EVIDENCE_UNAVAILABLE"
    missing["rows"][1]["reason"] = "FETCH_FAILED"
    missing["rows"][1]["byte_count"] = 0
    missing["missing_required_kinds"] = ["invoice"]
    # The invoice is a required kind, so the panel could not have run.
    assert module._parse_payload(_restate(module, context, missing),
                                 context, None, None) is None


def test_a_status_without_its_reason_is_refused(module, adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["rows"][0]["reason"] = "TOO_LARGE"
    assert module._parse_payload(forged, context, None, None) is None
    forged = copy.deepcopy(payload)
    forged["policy_reason"] = "HASH_MISMATCH"
    assert module._parse_payload(forged, context, None, None) is None


def test_a_missing_kinds_list_that_the_rows_do_not_support_is_refused(
        module, adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["missing_required_kinds"] = ["invoice"]
    assert module._parse_payload(forged, context, None, None) is None


def test_an_unassessed_round_is_never_a_coverage_verdict(module,
                                                         adjudicated):
    """`_derive_verdict` refuses to call an unread round a reading, whatever
    the rows say. Nothing in the pipeline can produce this payload - the
    gate above rejects it first - which is why the rule is tested here."""
    _harness, _policy, _submission, context, payload = adjudicated
    for state in ["INVALID", "SKIPPED"]:
        unread = copy.deepcopy(payload)
        unread["panel_state"] = state
        assert unread["findings"]["conditions"][0]["finding"] == "MET"
        assert module._derive_verdict(context, unread) == "INCONCLUSIVE"


def test_an_unexamined_document_is_never_a_coverage_verdict(module,
                                                            adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    for reason in ["FETCH_FAILED", "HASH_MISMATCH", "TOO_LARGE",
                   "UNREADABLE"]:
        unavailable = copy.deepcopy(payload)
        unavailable["policy_status"] = "EVIDENCE_UNAVAILABLE"
        unavailable["policy_reason"] = reason
        assert module._derive_verdict(context, unavailable) \
            == "EVIDENCE_UNAVAILABLE"
        assert module._evidence_status(unavailable) == "EVIDENCE_UNAVAILABLE"

    missing = copy.deepcopy(payload)
    missing["missing_required_kinds"] = ["invoice"]
    assert module._derive_verdict(context, missing) == "EVIDENCE_UNAVAILABLE"


def test_a_trigger_state_that_does_not_follow_is_refused(module,
                                                         adjudicated):
    """This policy declares no trigger, so NOT_DECLARED is the only state
    its payload may carry."""
    _harness, _policy, _submission, context, payload = adjudicated
    assert payload["trigger_state"] == "NOT_DECLARED"
    for state in ["MET", "NOT_MET", "UNREADABLE"]:
        forged = copy.deepcopy(payload)
        forged["trigger_state"] = state
        assert module._parse_payload(forged, context, None, None) is None


def test_a_trigger_state_must_follow_the_measurement(harness):
    """On a policy that does declare a trigger, the state must be the one
    the comparison produces. Staged here because a policy without a trigger
    refuses any state but NOT_DECLARED for a different reason."""
    import sys

    from conftest import (CROP_DEFINITION, CROP_EVIDENCE, CROP_INCIDENT,
                          HOLDING_STATEMENT, POLICY_CROP, RAINFALL_RECORD,
                          quote_from)

    rainfall = quote_from(RAINFALL_RECORD, "Cumulative rainfall recorded: 486")
    holding = quote_from(HOLDING_STATEMENT, "This claim is made for the")
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    claim_id = harness.open_challenge(
        policy_id, required=["holding_statement", "weather_record"])
    harness.mock_docs(POLICY_CROP, HOLDING_STATEMENT, RAINFALL_RECORD)
    submission_id = harness.submit(claim_id, evidence=CROP_EVIDENCE,
                                   incident=CROP_INCIDENT,
                                   reference="SYN-3017")
    harness.mock_panel(harness.panel(
        [("C1", "MET", holding, "E1"), ("C2", "MET", rainfall, "E2")],
        [("X1", "NOT_EVIDENCED", "", "")],
        trigger={"value_found": True, "value": 486, "quote": rainfall,
                 "evidence_id": "E2"}))
    # 486 millimetres against a threshold of at most 220.
    assert harness.resolve(submission_id) == "COVERAGE_NOT_ESTABLISHED"

    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get(submission_id)
    context = harness.contract._context(record)
    context["round"] = int(record.rounds_used)
    payload = json.loads(harness.contract.get_receipt(submission_id, 1))
    assert payload["trigger_state"] == "NOT_MET"
    assert module._parse_payload(payload, context, None, None) is not None

    # The same measurement, relabelled as a trigger that fired.
    forged = copy.deepcopy(payload)
    forged["trigger_state"] = "MET"
    assert module._parse_payload(_restate(module, context, forged),
                                 context, None, None) is None
    forged = copy.deepcopy(payload)
    forged["trigger_state"] = "UNREADABLE"
    assert module._parse_payload(_restate(module, context, forged),
                                 context, None, None) is None


def test_an_outcome_that_does_not_follow_from_the_findings_is_refused(
        module, adjudicated):
    """The gate re-derives the verdict and the criteria. A leader cannot
    report an outcome its own findings do not produce - which is what makes
    it safe for validators to compare the outcome rather than every label
    behind it."""
    _harness, _policy, _submission, context, payload = adjudicated
    for verdict in ["COVERAGE_NOT_ESTABLISHED", "EXCLUSION_APPLIES",
                    "INCONCLUSIVE", "FRAUD_INDICATORS_FOUND"]:
        forged = copy.deepcopy(payload)
        forged["verdict"] = verdict
        assert module._parse_payload(forged, context, None, None) is None
    for field in ["policy_version_verified", "covered_event_supported",
                  "required_conditions_met", "exclusion_evidence_found"]:
        forged = copy.deepcopy(payload)
        forged["criteria"][field] = not forged["criteria"][field]
        assert module._parse_payload(forged, context, None, None) is None


def test_the_criteria_follow_the_findings(module, adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    # C1 is the covered-event condition; C2 is not.
    not_covered = copy.deepcopy(payload)
    not_covered["findings"]["conditions"][0]["finding"] = "NOT_MET"
    criteria = module._criteria(context, not_covered)
    assert criteria["covered_event_supported"] is False
    assert criteria["required_conditions_met"] is False

    other = copy.deepcopy(payload)
    other["findings"]["conditions"][1]["finding"] = "NOT_MET"
    criteria = module._criteria(context, other)
    assert criteria["covered_event_supported"] is True
    assert criteria["required_conditions_met"] is False

    excluded = copy.deepcopy(payload)
    excluded["findings"]["exclusions"][0]["finding"] = "EVIDENCED"
    assert module._criteria(context, excluded)["exclusion_evidence_found"] \
        is True


def test_the_same_claim_cannot_be_counted_twice(adjudicated):
    """The counters are a policy version's public record. A claim
    contributes to it once, however many times a result is recorded."""
    harness, policy_id, submission_id, context, payload = adjudicated
    before = harness.contract.policy_record(policy_id, 1)
    assert before["COVERAGE_SUPPORTED"] == 1
    assert before["total"] == 1
    assert harness.contract.get_stats()["resolved"] == 1

    record = harness.contract.submissions.get(submission_id)
    harness.contract._record(record, context, payload, "COVERAGE_SUPPORTED")

    assert harness.contract.policy_record(policy_id, 1) == before
    assert harness.contract.get_stats()["resolved"] == 1
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is True
