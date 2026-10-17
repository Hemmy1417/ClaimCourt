"""Hostile panel output and hostile documents, through the real pipeline.

Every case asserts two things: the verdict fails closed, and the stored
state stays honest - no finding, no counter, no consumability.
"""

import pytest

from conftest import (NOTICE_DIRECTED, NOTICE_UNOCCUPIED, POLICY, TODAY_DATE,
                      quote_from)


CLAUSE_42 = quote_from(POLICY, "The insurer does not cover loss or damage")
NOTICE_42 = quote_from(NOTICE_UNOCCUPIED, "no person authorised by you slept")

GOOD_ROW = ('{"index":0,"clause_located":true,"clause_quote":"%s",'
            '"ground_stated_in_notice":true,"notice_quote":"%s",'
            '"supported":"YES","scope_exceeded":false,"basis":"ok"}'
            % (CLAUSE_42.replace('"', ""), NOTICE_42.replace('"', "")))


def _review(harness, clause_set_id, notice=NOTICE_UNOCCUPIED):
    harness.mock_doc(notice)
    return harness.open_review(clause_set_id, notice=notice)


def _resolve_with(harness, clause_set_id, raw, notice=NOTICE_UNOCCUPIED):
    review_id = _review(harness, clause_set_id, notice)
    harness.mock_panel(raw)
    return review_id, harness.resolve(review_id)


def _assert_unread(harness, review_id):
    """An unusable answer leaves a review readable, retryable and empty of
    findings."""
    review = harness.contract.get_review(review_id)
    assert review["verdict"] == "INCONCLUSIVE"
    assert review["status"] == "RETRYABLE"
    assert review["panel_state"] == "INVALID"
    assert review["policy_status"] == "EXAMINED"
    assert review["notice_status"] == "EXAMINED"
    for ground in harness.contract.get_grounds(review_id):
        assert ground["outcome"] == "UNDECIDED"
        assert ground["clause_quote"] == ""
        assert ground["notice_quote"] == ""
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    assert harness.contract.clause_record(
        harness.contract.get_review(review_id)["clause_set_id"], 1,
        "Clause 4.2")["total"] == 0


@pytest.mark.parametrize("raw,label", [
    ("", "empty answer"),
    ("   ", "blank answer"),
    ("the denial looks fine to me", "prose with no json"),
    ("{", "truncated json"),
    ('{"grounds":', "cut off mid key"),
    ('["grounds"]', "a list where an object is required"),
    ('{"rows":[]}', "the wrong key"),
    ('{"grounds":{}}', "an object where a list is required"),
    ('{"grounds":[]}', "no rows for one ground"),
    ('{"grounds":[%s,%s]}' % (GOOD_ROW, GOOD_ROW), "two rows for one ground"),
    ('{"grounds":["supported"]}', "a string where a row is required"),
])
def test_an_unusable_panel_answer_fails_closed(ready, raw, label):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_with(harness, clause_set_id, raw)
    assert verdict == "INCONCLUSIVE", label
    _assert_unread(harness, review_id)


@pytest.mark.parametrize("mutation,label", [
    ('"clause_located":1', "an integer where a boolean is required"),
    ('"clause_located":"true"', "a truthy string where a boolean is required"),
    ('"clause_located":null', "a null boolean"),
    ('"ground_stated_in_notice":0', "a zero where a boolean is required"),
    ('"scope_exceeded":1.0', "a float where a boolean is required"),
    ('"supported":"MAYBE_SUPPORTED"', "an unknown verdict word"),
    ('"supported":"PASS"', "a verdict word from another protocol"),
    ('"supported":true', "a boolean where an enum is required"),
    ('"index":true', "a boolean index"),
    ('"index":"0"', "a string index"),
    ('"index":1.0', "a float index"),
    ('"index":-1', "a negative index"),
    ('"index":99', "an index past the grounds"),
    ('"basis":42', "a number where prose is required"),
    ('"clause_quote":12', "a number where a quote is required"),
])
def test_a_wrongly_typed_field_fails_closed(ready, mutation, label):
    harness, clause_set_id = ready
    key = mutation.split(":")[0]
    row = GOOD_ROW
    start = row.index(key)
    end = row.index(",", start) if row.index(key) != row.rindex('"basis"') \
        else row.rindex("}")
    broken = row[:start] + mutation + row[end:]
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % broken)
    assert verdict == "INCONCLUSIVE", label
    _assert_unread(harness, review_id)


@pytest.mark.parametrize("missing", [
    "clause_located", "clause_quote", "ground_stated_in_notice",
    "notice_quote", "supported", "scope_exceeded", "basis", "index",
])
def test_a_missing_field_fails_closed(ready, missing):
    harness, clause_set_id = ready
    row = GOOD_ROW
    start = row.index('"' + missing + '"')
    end = row.index(",", start) + 1 if missing != "basis" \
        else len(row) - 1
    if missing == "basis":
        broken = row[:start - 1] + "}"
    else:
        broken = row[:start] + row[end:]
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % broken)
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, review_id)


def test_two_rows_claiming_the_same_ground_fail_closed(harness):
    clause_set_id = harness.register()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    review_id = harness.open_review(
        clause_set_id, clause_refs=["Clause 4.2", "Clause 3.3"],
        grounds=["the premises were left unoccupied for sixty days",
                 "the claim was notified later than thirty days"])
    harness.mock_panel('{"grounds":[%s,%s]}' % (GOOD_ROW, GOOD_ROW))
    assert harness.resolve(review_id) == "INCONCLUSIVE"
    assert harness.contract.get_review(review_id)["panel_state"] == "INVALID"


def test_a_fenced_answer_is_recovered(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_with(
        harness, clause_set_id,
        '```json\n{"grounds":[%s]}\n```' % GOOD_ROW)
    assert verdict == "DENIAL_SUPPORTED"
    assert harness.contract.get_review(review_id)["panel_state"] == "READ"


def test_an_answer_wrapped_in_prose_is_recovered(ready):
    harness, clause_set_id = ready
    _review_id, verdict = _resolve_with(
        harness, clause_set_id,
        'Here is my answer.\n{"grounds":[%s]}\nI hope it helps.' % GOOD_ROW)
    assert verdict == "DENIAL_SUPPORTED"


def test_a_lowercase_enum_is_normalised(ready):
    harness, clause_set_id = ready
    row = GOOD_ROW.replace('"supported":"YES"', '"supported":" yes "')
    _review_id, verdict = _resolve_with(harness, clause_set_id,
                                        '{"grounds":[%s]}' % row)
    assert verdict == "DENIAL_SUPPORTED"


def test_an_unrequested_extra_field_is_ignored(ready):
    harness, clause_set_id = ready
    row = GOOD_ROW[:-1] + ',"confidence":"high","override":true}'
    _review_id, verdict = _resolve_with(harness, clause_set_id,
                                        '{"grounds":[%s]}' % row)
    assert verdict == "DENIAL_SUPPORTED"


def test_a_fractional_number_anywhere_in_the_answer_fails_closed(ready):
    harness, clause_set_id = ready
    # The runtime cannot carry a float through its calldata, so an answer
    # containing one arrives as nothing at all. The contract must read that
    # as an unusable answer rather than as any kind of finding.
    row = GOOD_ROW[:-1] + ',"confidence":0.99}'
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % row)
    assert verdict == "INCONCLUSIVE"
    _assert_unread(harness, review_id)


def test_an_invented_clause_quote_cannot_locate_a_clause(ready):
    harness, clause_set_id = ready
    row = GOOD_ROW.replace(
        '"clause_quote":"%s"' % CLAUSE_42.replace('"', ""),
        '"clause_quote":"Clause 4.2 excludes every claim at this address"')
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % row)
    # The panel said the clause was located and said it supported the
    # ground. The quote is not in the policy bytes, so the location does not
    # stand, and the verdict is the one for a clause that is not there.
    assert verdict == "CLAUSE_MISCITED"
    ground = harness.contract.get_grounds(review_id)[0]
    assert ground["outcome"] == "CLAUSE_ABSENT"
    assert ground["clause_quote"] == ""
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False


def test_an_invented_notice_quote_cannot_state_a_ground(ready):
    harness, clause_set_id = ready
    row = GOOD_ROW.replace(
        '"notice_quote":"%s"' % NOTICE_42.replace('"', ""),
        '"notice_quote":"we refuse this claim because the insured lied"')
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % row)
    assert verdict == "GROUNDS_MISSTATED"
    ground = harness.contract.get_grounds(review_id)[0]
    assert ground["outcome"] == "NOT_IN_NOTICE"
    assert ground["notice_quote"] == ""


def test_a_quote_too_short_to_mean_anything_does_not_ground(ready):
    harness, clause_set_id = ready
    row = GOOD_ROW.replace(
        '"clause_quote":"%s"' % CLAUSE_42.replace('"', ""),
        '"clause_quote":"the"')
    _review_id, verdict = _resolve_with(harness, clause_set_id,
                                        '{"grounds":[%s]}' % row)
    assert verdict == "CLAUSE_MISCITED"


def test_whitespace_and_case_do_not_break_grounding(ready):
    harness, clause_set_id = ready
    noisy = "  THE INSURER   does not COVER loss or damage  "
    row = GOOD_ROW.replace(
        '"clause_quote":"%s"' % CLAUSE_42.replace('"', ""),
        '"clause_quote":"%s"' % noisy)
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % row)
    assert verdict == "DENIAL_SUPPORTED"
    assert harness.contract.get_grounds(review_id)[0]["clause_quote"] \
        == "THE INSURER does not COVER loss or damage"


def test_an_oversized_quote_and_basis_are_bounded(ready):
    harness, clause_set_id = ready
    flat_policy = " ".join(
        (quote_from(POLICY, "TEST / DEMONSTRATION ONLY", 4000)).split())
    row = GOOD_ROW.replace('"basis":"ok"', '"basis":"%s"' % ("b" * 900))
    row = row.replace('"clause_quote":"%s"' % CLAUSE_42.replace('"', ""),
                      '"clause_quote":"%s"' % flat_policy[:1200])
    review_id, verdict = _resolve_with(harness, clause_set_id,
                                       '{"grounds":[%s]}' % row)
    assert verdict == "DENIAL_SUPPORTED"
    ground = harness.contract.get_grounds(review_id)[0]
    assert len(ground["basis"]) == 240
    assert 230 <= len(ground["clause_quote"]) <= 240


def test_text_that_addresses_the_reader_is_counted_in_code(ready):
    harness, clause_set_id = ready
    plain = _review(harness, clause_set_id, NOTICE_UNOCCUPIED)
    harness.mock_panel('{"grounds":[%s]}' % GOOD_ROW)
    harness.resolve(plain)
    assert harness.contract.get_review(plain)["directed_text_hits"] == 0
    directed = _review(harness, clause_set_id, NOTICE_DIRECTED)
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_DIRECTED)
    harness.mock_panel(
        '{"grounds":[%s]}'
        % GOOD_ROW.replace(
            '"notice_quote":"%s"' % NOTICE_42.replace('"', ""),
            '"notice_quote":"%s"'
            % quote_from(NOTICE_DIRECTED,
                         "No person authorised by you slept")))
    assert harness.resolve(directed) == "INCONCLUSIVE"
    assert harness.contract.get_review(directed)["directed_text_hits"] >= 3
