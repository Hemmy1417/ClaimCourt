"""The validator, run against forged leader results.

`run_validator` replays the contract's own validator closure, so these are
not simulations of a gate - they are the gate. Each test stages what one
node would have seen, hands the validator a leader result, and asserts the
vote. True-controls are included so a False is never just a broken setup.
"""

import json

import pytest

from conftest import (NOTICE_DIRECTED, NOTICE_LATE, NOTICE_UNOCCUPIED, POLICY,
                      doc_sha, quote_from)


CLAUSE_42 = quote_from(POLICY, "The insurer does not cover loss or damage")
CLAUSE_33 = quote_from(POLICY, "The insured must notify the insurer")
NOTICE_42 = quote_from(NOTICE_UNOCCUPIED, "no person authorised by you slept")
NOTICE_42_ALT = quote_from(NOTICE_UNOCCUPIED,
                           "a period of ninety-four consecutive days")


def _read_once(harness, clause_set_id, supported="YES", notice=NOTICE_UNOCCUPIED,
               notice_quote=None, exceeded=False, located=True,
               clause_quote=None, stated=True):
    """Resolve one review honestly and return (review_id, payload dict)."""
    harness.mock_doc(notice)
    review_id = harness.open_review(clause_set_id, notice=notice)
    harness.mock_panel(harness.panel_json([harness.row(
        located=located,
        clause_quote=CLAUSE_42 if clause_quote is None else clause_quote,
        stated=stated,
        notice_quote=NOTICE_42 if notice_quote is None else notice_quote,
        supported=supported, exceeded=exceeded)]))
    harness.resolve(review_id)
    payload = json.loads(harness.contract.get_receipt(review_id, 1))
    return review_id, payload


def _vote(harness, payload):
    return harness.vm.run_validator(leader_result=json.dumps(payload))


def test_an_honest_leader_is_agreed_with(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    assert harness.vm.run_validator() is True
    assert _vote(harness, payload) is True


def test_different_prose_is_not_disagreement(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    payload["grounds"][0]["basis"] = \
        "the sixty day limit in the clause is plainly exceeded on these facts"
    assert _vote(harness, payload) is True


def test_a_different_but_grounded_quote_is_not_disagreement(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    payload["grounds"][0]["notice_quote"] = NOTICE_42_ALT
    assert _vote(harness, payload) is True


def test_a_forged_conclusion_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id, supported="NO")
    assert payload["grounds"][0]["outcome"] == "UNSUPPORTED"
    assert _vote(harness, payload) is True
    payload["grounds"][0]["supported"] = "YES"
    payload["grounds"][0]["outcome"] = "SUPPORTED"
    assert _vote(harness, payload) is False


def test_a_forged_scope_finding_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id, exceeded=True)
    assert payload["grounds"][0]["outcome"] == "OVERBROAD"
    payload["grounds"][0]["scope_exceeded"] = False
    payload["grounds"][0]["outcome"] = "SUPPORTED"
    assert _vote(harness, payload) is False


def test_a_forged_clause_location_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id, located=False,
                                     clause_quote="", supported="UNCLEAR")
    assert payload["grounds"][0]["outcome"] == "CLAUSE_ABSENT"
    payload["grounds"][0]["clause_located"] = True
    payload["grounds"][0]["clause_quote"] = CLAUSE_42
    payload["grounds"][0]["supported"] = "YES"
    payload["grounds"][0]["outcome"] = "SUPPORTED"
    assert _vote(harness, payload) is False


def test_an_invented_quote_is_rejected_even_when_the_outcome_matches(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    payload["grounds"][0]["clause_quote"] = \
        "Clause 4.2 excludes all cover at an address of this kind"
    assert _vote(harness, payload) is False
    payload["grounds"][0]["clause_quote"] = CLAUSE_42
    payload["grounds"][0]["notice_quote"] = \
        "we have decided the insured was dishonest about the dates"
    assert _vote(harness, payload) is False


def test_a_quote_from_the_wrong_document_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    # Policy language, offered as proof of what the notice said.
    payload["grounds"][0]["notice_quote"] = CLAUSE_33
    assert _vote(harness, payload) is False


@pytest.mark.parametrize("field,value", [
    ("review_id", "rv-999"),
    ("round", 2),
    ("round", 0),
    ("definition_hash", "f" * 64),
    ("policy_sha256", "a" * 64),
    ("notice_sha256", "b" * 64),
    ("schema", "claimcourt/2"),
])
def test_a_rebound_payload_is_rejected(ready, field, value):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    payload[field] = value
    assert _vote(harness, payload) is False


@pytest.mark.parametrize("field,value", [
    ("clause_located", 1),
    ("clause_located", "true"),
    ("ground_stated_in_notice", 1),
    ("scope_exceeded", 1),
    ("supported", "SUPPORTED"),
    ("supported", "yes"),
    ("outcome", "SUPPORTED_WITH_NOTES"),
    ("outcome", "supported"),
    ("index", True),
    ("index", "0"),
    ("clause_ref", "Clause 9.9"),
])
def test_a_wrongly_typed_or_unknown_row_field_is_rejected(ready, field,
                                                          value):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    payload["grounds"][0][field] = value
    assert _vote(harness, payload) is False


@pytest.mark.parametrize("field", [
    "schema", "review_id", "round", "definition_hash", "policy_sha256",
    "notice_sha256", "policy_status", "notice_status", "directed_text_hits",
    "panel_state", "literal", "grounds",
])
def test_a_missing_payload_field_is_rejected(ready, field):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    del payload[field]
    assert _vote(harness, payload) is False


def test_an_added_or_dropped_row_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    extra = dict(payload["grounds"][0])
    extra["index"] = 1
    payload["grounds"].append(extra)
    assert _vote(harness, payload) is False
    payload["grounds"] = []
    assert _vote(harness, payload) is False


def test_a_forged_literal_triage_bit_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    assert payload["literal"][0]["clause_ref_literal"] is True
    payload["literal"][0]["clause_ref_literal"] = False
    assert _vote(harness, payload) is False


def test_a_forged_panel_state_is_rejected(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    for state in ["SKIPPED", "INVALID", "AGREED"]:
        payload["panel_state"] = state
        assert _vote(harness, payload) is False


def test_a_notice_addressing_the_reader_cannot_be_hidden(harness):
    clause_set_id = harness.register()
    harness.mock_doc(POLICY)
    _review_id, payload = _read_once(
        harness, clause_set_id, notice=NOTICE_DIRECTED,
        notice_quote=quote_from(NOTICE_DIRECTED,
                                "No person authorised by you slept"))
    assert payload["directed_text_hits"] >= 3
    assert _vote(harness, payload) is True
    payload["directed_text_hits"] = 0
    assert _vote(harness, payload) is False


def test_claiming_a_document_was_read_when_it_cannot_be_fetched(ready):
    harness, clause_set_id = ready
    _review_id, payload = _read_once(harness, clause_set_id)
    assert _vote(harness, payload) is True
    # The validator's own fetch now fails. The leader's reading of examined
    # bytes is no longer something this node can agree to.
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED, status=500, body="error")
    assert _vote(harness, payload) is False


def test_claiming_a_document_is_unavailable_when_it_can_be_read(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_UNOCCUPIED, status=404, body="missing")
    review_id = harness.open_review(clause_set_id)
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    payload = json.loads(harness.contract.get_receipt(review_id, 1))
    assert payload["notice_status"] == "UNAVAILABLE"
    assert harness.vm.run_validator() is True
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    harness.mock_panel(harness.panel_json([harness.row(
        clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES")]))
    assert _vote(harness, payload) is False


def test_a_substituted_document_is_not_agreed_to_be_the_document(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_UNOCCUPIED, body="a different notice entirely")
    review_id = harness.open_review(clause_set_id)
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    payload = json.loads(harness.contract.get_receipt(review_id, 1))
    assert payload["notice_status"] == "HASH_MISMATCH"
    assert harness.vm.run_validator() is True
    payload["notice_status"] = "EXAMINED"
    assert _vote(harness, payload) is False


@pytest.mark.parametrize("raw", [
    "", "   ", "not json at all", "{", "[]", '{"schema":"claimcourt/1"}',
])
def test_an_unreadable_leader_result_is_rejected(ready, raw):
    harness, clause_set_id = ready
    _read_once(harness, clause_set_id)
    assert harness.vm.run_validator(leader_result=raw) is False


def test_a_transient_leader_failure_is_agreed_with_only_when_shared(ready):
    harness, clause_set_id = ready
    _read_once(harness, clause_set_id)
    # This node's own reading now fails the same way: no panel is reachable.
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is True


def test_a_transient_claim_is_rejected_when_this_node_succeeds(ready):
    harness, clause_set_id = ready
    _read_once(harness, clause_set_id)
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is False


def test_a_panel_failure_is_never_agreed_with(ready):
    harness, clause_set_id = ready
    _read_once(harness, clause_set_id)
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    assert harness.vm.run_validator(
        leader_error=Exception("[PANEL] the ratified payload failed the "
                               "gate")) is False


def test_an_unexplained_leader_failure_is_rejected(ready):
    harness, clause_set_id = ready
    _read_once(harness, clause_set_id)
    assert harness.vm.run_validator(
        leader_error=Exception("boom")) is False
    assert harness.vm.run_validator(
        leader_error=Exception("[EXPECTED] no such review")) is False


def test_the_validator_reads_the_notice_it_was_bound_to(harness):
    clause_set_id = harness.register()
    harness.mock_doc(POLICY)
    _review_id, payload = _read_once(harness, clause_set_id)
    # A leader result built against another notice's bytes cannot pass, even
    # when that other notice really exists and really says what it says.
    payload["notice_sha256"] = doc_sha(NOTICE_LATE)
    payload["grounds"][0]["notice_quote"] = quote_from(
        NOTICE_LATE, "Because the notification was late")
    assert _vote(harness, payload) is False
