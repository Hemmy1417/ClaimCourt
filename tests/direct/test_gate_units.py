"""The gate, exercised directly.

Four of the contract's rules are second lines of defence: in a normal round
the validator's field-by-field comparison catches the same attack first, so
removing them changes no end-to-end result. They still matter - the ratified
payload is parsed once more after consensus, where there is no validator left
to compare against - and a rule nothing exercises is a rule nothing protects.

These tests call `_parse_payload`, `_derive_verdict` and `_record_outcome`
with staged inputs, so each rule is responsible for its own failure. The
mutation sweep in `scripts/mutate.py` removes each one; every mutation below
is killed here.
"""

import copy
import json
import sys

import pytest

from conftest import NOTICE_UNOCCUPIED, POLICY, TODAY_DATE, quote_from


CLAUSE_42 = quote_from(POLICY, "The insurer does not cover loss or damage")
NOTICE_42 = quote_from(NOTICE_UNOCCUPIED, "no person authorised by you slept")


@pytest.fixture
def read(ready):
    """A settled review, plus the context and payload the round used."""
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_UNOCCUPIED)
    review_id = harness.open_review(clause_set_id)
    harness.mock_panel(harness.panel_json([harness.row(
        clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES")]))
    assert harness.resolve(review_id) == "DENIAL_SUPPORTED"
    record = harness.contract.reviews.get(review_id)
    context = harness.contract._context(record)
    # _context is built for the NEXT round; the payload is from the last one.
    context["round"] = int(record.rounds_used)
    payload = json.loads(harness.contract.get_receipt(review_id, 1))
    return harness, clause_set_id, review_id, context, payload


@pytest.fixture
def module(read):
    """The contract's own module, as Direct Mode loaded it. Derived from the
    deployed class rather than named, so the mutation sweep - which loads a
    patched copy under its own name - exercises these tests too."""
    harness = read[0]
    return sys.modules[type(harness.contract).__module__]


def test_the_honest_payload_passes_the_gate(module, read):
    """The control. Without this, every rejection below could be a staging
    error rather than a rule doing its job."""
    _harness, _set, _review, context, payload = read
    parsed = module._parse_payload(payload, context, None, None)
    assert parsed is not None
    assert parsed["grounds"][0]["outcome"] == "SUPPORTED"
    assert module._derive_verdict(parsed) == "DENIAL_SUPPORTED"


def test_a_row_whose_outcome_contradicts_its_own_fields_is_refused(module,
                                                                   read):
    """A leader cannot name an outcome its own row does not support. The
    fields here say the clause does not reach the ground; the outcome claims
    it does."""
    _harness, _set, _review, context, payload = read
    forged = copy.deepcopy(payload)
    forged["grounds"][0]["supported"] = "NO"
    forged["grounds"][0]["outcome"] = "SUPPORTED"
    assert module._parse_payload(forged, context, None, None) is None

    # ... and the same row with its own outcome is accepted, so the rule is
    # about the contradiction and not about the value.
    honest = copy.deepcopy(payload)
    honest["grounds"][0]["supported"] = "NO"
    honest["grounds"][0]["outcome"] = "UNSUPPORTED"
    parsed = module._parse_payload(honest, context, None, None)
    assert parsed is not None
    assert module._derive_verdict(parsed) == "DENIAL_UNSUPPORTED"


def test_a_round_that_did_not_read_cannot_carry_a_finding(module, read):
    """When the panel did not answer, every row has exactly one permitted
    shape. A finding on such a round is a fabrication."""
    _harness, _set, _review, context, payload = read
    for state in ["INVALID", "SKIPPED"]:
        forged = copy.deepcopy(payload)
        forged["panel_state"] = state
        # the row still claims the clause was located and the ground stood
        assert module._parse_payload(forged, context, None, None) is None

    unread = copy.deepcopy(payload)
    unread["panel_state"] = "INVALID"
    unread["grounds"][0].update({
        "clause_located": False, "clause_quote": "",
        "ground_stated_in_notice": False, "notice_quote": "",
        "supported": "UNCLEAR", "scope_exceeded": False,
        "outcome": "UNDECIDED"})
    parsed = module._parse_payload(unread, context, None, None)
    assert parsed is not None, "the permitted shape must still be accepted"
    assert module._derive_verdict(parsed) == "INCONCLUSIVE"


def test_a_panel_state_that_contradicts_the_documents_is_refused(module,
                                                                 read):
    """A reading cannot have happened on bytes nobody could examine, and a
    round where both documents were examined cannot report the panel as
    skipped."""
    _harness, _set, _review, context, payload = read

    unreadable = copy.deepcopy(payload)
    unreadable["notice_status"] = "UNAVAILABLE"
    assert unreadable["panel_state"] == "READ"
    assert module._parse_payload(unreadable, context, None, None) is None

    skipped = copy.deepcopy(payload)
    skipped["panel_state"] = "SKIPPED"
    skipped["grounds"][0].update({
        "clause_located": False, "clause_quote": "",
        "ground_stated_in_notice": False, "notice_quote": "",
        "supported": "UNCLEAR", "scope_exceeded": False,
        "outcome": "UNDECIDED"})
    assert module._parse_payload(skipped, context, None, None) is None


def test_an_unread_round_is_never_a_finding(module, read):
    """`_derive_verdict` refuses to call an unread round a reading, whatever
    the rows say. Nothing in the pipeline can produce this payload - the gate
    above rejects it first - which is exactly why the rule is tested here."""
    _harness, _set, _review, _context, payload = read
    for state in ["INVALID", "SKIPPED"]:
        unread = copy.deepcopy(payload)
        unread["panel_state"] = state
        assert unread["grounds"][0]["outcome"] == "SUPPORTED"
        assert module._derive_verdict(unread) == "INCONCLUSIVE"

    examined = copy.deepcopy(payload)
    assert module._derive_verdict(examined) == "DENIAL_SUPPORTED"


def test_a_document_that_was_not_examined_is_never_a_finding(module, read):
    """The same rule for the other half of the round."""
    _harness, _set, _review, _context, payload = read
    for field in ["policy_status", "notice_status"]:
        for status in ["UNAVAILABLE", "HASH_MISMATCH", "TOO_LARGE",
                       "UNREADABLE"]:
            unavailable = copy.deepcopy(payload)
            unavailable[field] = status
            assert module._derive_verdict(unavailable) == "RECORD_UNAVAILABLE"


def test_the_same_review_cannot_be_counted_twice(read):
    """The counters are a clause's public record. A review contributes to it
    once, however many times a result is recorded against it."""
    harness, clause_set_id, review_id, _context, payload = read
    before = harness.contract.clause_record(clause_set_id, 1, "Clause 4.2")
    assert before["SUPPORTED"] == 1
    assert before["total"] == 1
    summary = harness.contract.clause_set_record(clause_set_id, 1)
    assert summary["DENIAL_SUPPORTED"] == 1
    assert harness.contract.get_stats()["resolved"] == 1

    record = harness.contract.reviews.get(review_id)
    harness.contract._record_outcome(record, payload, "DENIAL_SUPPORTED")

    after = harness.contract.clause_record(clause_set_id, 1, "Clause 4.2")
    assert after == before
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_SUPPORTED"] == 1
    assert harness.contract.get_stats()["resolved"] == 1
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is True
