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
        assert module._parse_payload(forged, context, None, None) is None

    # The uncertain form may carry no quote, which is the whole point of it.
    unclear = copy.deepcopy(payload)
    unclear["findings"]["conditions"][0]["finding"] = "UNCLEAR"
    unclear["findings"]["conditions"][0]["quote"] = ""
    unclear["findings"]["conditions"][0]["evidence_id"] = ""
    parsed = module._parse_payload(unclear, context, None, None)
    assert parsed is not None
    assert module._derive_verdict(context, parsed) == "INCONCLUSIVE"


def test_an_evidenced_exclusion_without_its_words_is_refused(module,
                                                             adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["exclusions"][0]["finding"] = "EVIDENCED"
    forged["findings"]["exclusions"][0]["quote"] = ""
    assert module._parse_payload(forged, context, None, None) is None


def test_an_accusation_without_its_words_is_refused(module, adjudicated):
    _harness, _policy, _submission, context, payload = adjudicated
    forged = copy.deepcopy(payload)
    forged["findings"]["fraud"]["finding"] = "INDICATORS_FOUND"
    forged["findings"]["fraud"]["quote"] = ""
    assert module._parse_payload(forged, context, None, None) is None


def test_a_round_that_did_not_assess_cannot_carry_a_finding(module,
                                                            adjudicated):
    """When the panel did not answer, every row has one permitted shape."""
    _harness, _policy, _submission, context, payload = adjudicated
    for state in ["INVALID", "SKIPPED"]:
        forged = copy.deepcopy(payload)
        forged["panel_state"] = state
        assert module._parse_payload(forged, context, None, None) is None

    unread = copy.deepcopy(payload)
    unread["panel_state"] = "INVALID"
    for row in unread["findings"]["conditions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    for row in unread["findings"]["exclusions"]:
        row.update({"finding": "NOT_ASSESSED", "quote": "", "evidence_id": ""})
    unread["findings"]["evidence"].update(
        {"sufficient": False, "contradiction": False, "quote": "",
         "evidence_id": ""})
    parsed = module._parse_payload(unread, context, None, None)
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
    assert module._parse_payload(unreadable, context, None, None) is None

    missing = copy.deepcopy(payload)
    missing["rows"][1]["status"] = "EVIDENCE_UNAVAILABLE"
    missing["rows"][1]["reason"] = "FETCH_FAILED"
    missing["rows"][1]["byte_count"] = 0
    # The invoice is a required kind, so the panel could not have run.
    assert module._parse_payload(missing, context, None, None) is None


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
