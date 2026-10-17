"""Every verdict the contract can reach, derived from a mocked reading of
real fixture bytes. The panel's answer is mocked; the admission, grounding,
precedence, storage and counter code under test is the contract's own."""

import json

from conftest import (NOTICE_DIRECTED, NOTICE_FLOOD, NOTICE_JEWELLERY,
                      NOTICE_LATE, NOTICE_UNOCCUPIED, POLICY, TODAY_DATE,
                      doc_sha, doc_text, quote_from, sha_of,
                      url_for)


CLAUSE_42 = quote_from(POLICY, "The insurer does not cover loss or damage")
CLAUSE_33 = quote_from(POLICY, "The insured must notify the insurer")
CLAUSE_54 = quote_from(POLICY, "Cover for jewellery is limited")
NOTICE_42 = quote_from(NOTICE_UNOCCUPIED, "no person authorised by you slept")
NOTICE_33 = quote_from(NOTICE_LATE, "Because the notification was late")
NOTICE_54 = quote_from(NOTICE_JEWELLERY, "we are declining the claim in its")
NOTICE_94 = quote_from(NOTICE_FLOOD, "Clause 9.4 of the wording excludes")
NOTICE_DIR = quote_from(NOTICE_DIRECTED, "No person authorised by you slept")

LATE_GROUND = ["the claim was notified after thirty days so the cover ended"]
JEWELLERY_GROUND = ["the whole claim is declined because the jewellery limit "
                    "was exceeded"]
FLOOD_GROUND = ["the loss was caused by flood or rising groundwater"]


def _resolve_one(harness, clause_set_id, notice, clause_refs, grounds,
                 row_kwargs, reference="SYN-TEST"):
    harness.mock_doc(notice)
    review_id = harness.open_review(clause_set_id, notice=notice,
                                    clause_refs=clause_refs, grounds=grounds,
                                    reference=reference)
    harness.mock_panel(harness.panel_json([harness.row(**row_kwargs)]))
    verdict = harness.resolve(review_id)
    return review_id, verdict


def test_a_ground_the_clause_reaches_is_supported(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42,
             supported="YES"))
    assert verdict == "DENIAL_SUPPORTED"
    review = harness.contract.get_review(review_id)
    assert review["status"] == "RESOLVED"
    assert review["verdict"] == "DENIAL_SUPPORTED"
    assert review["policy_status"] == "EXAMINED"
    assert review["notice_status"] == "EXAMINED"
    assert review["panel_state"] == "READ"
    assert review["rounds_used"] == 1
    assert review["resolved_on"] == TODAY_DATE
    assert review["directed_text_hits"] == 0
    ground = harness.contract.get_grounds(review_id)[0]
    assert ground["outcome"] == "SUPPORTED"
    assert ground["clause_quote"] == " ".join(CLAUSE_42.split())
    assert ground["clause_ref_literal"] is True
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is True
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is False
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is True
    assert harness.contract.freshness(review_id, TODAY_DATE) == "RELIABLE"
    outcome = harness.contract.review_outcome(review_id, TODAY_DATE)
    assert outcome["grounds_supported"] == 1
    assert outcome["grounds_failing"] == 0
    assert outcome["is_current_version"] is True
    record = harness.contract.clause_record(clause_set_id, 1, "Clause 4.2")
    assert record["SUPPORTED"] == 1
    assert record["total"] == 1
    summary = harness.contract.clause_set_record(clause_set_id, 1)
    assert summary["DENIAL_SUPPORTED"] == 1
    assert harness.contract.get_stats()["resolved"] == 1


def test_a_ground_the_clause_does_not_reach_is_unsupported(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_LATE, ["Clause 3.3"], LATE_GROUND,
        dict(clause_quote=CLAUSE_33, notice_quote=NOTICE_33, supported="NO"))
    assert verdict == "DENIAL_UNSUPPORTED"
    assert harness.contract.get_grounds(review_id)[0]["outcome"] \
        == "UNSUPPORTED"
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is True
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is True
    outcome = harness.contract.review_outcome(review_id, TODAY_DATE)
    assert outcome["grounds_failing"] == 1
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 3.3")["UNSUPPORTED"] == 1
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_UNSUPPORTED"] == 1


def test_a_clause_applied_past_its_scope_is_overbroad(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_JEWELLERY, ["Clause 5.4"],
        JEWELLERY_GROUND,
        dict(clause_quote=CLAUSE_54, notice_quote=NOTICE_54, supported="YES",
             exceeded=True))
    assert verdict == "DENIAL_OVERBROAD"
    assert harness.contract.get_grounds(review_id)[0]["outcome"] == "OVERBROAD"
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is True
    # Overbroad is neither a clean upholding nor a plain lack of support:
    # both convenience gates say no, and the consumer reads the verdict.
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is False
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_OVERBROAD"] == 1


def test_a_clause_that_is_not_in_the_version_is_miscited(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_FLOOD, ["Clause 9.4"], FLOOD_GROUND,
        dict(located=False, clause_quote="", notice_quote=NOTICE_94,
             supported="UNCLEAR"))
    assert verdict == "CLAUSE_MISCITED"
    ground = harness.contract.get_grounds(review_id)[0]
    assert ground["outcome"] == "CLAUSE_ABSENT"
    assert ground["clause_ref_literal"] is False
    assert ground["assertion_literal"] is False
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is True
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["CLAUSE_MISCITED"] == 1


def test_a_ground_the_notice_does_not_state_is_misstated(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"],
        ["the insured set fire to the premises deliberately"],
        dict(clause_quote=CLAUSE_42, stated=False, notice_quote="",
             supported="UNCLEAR"))
    assert verdict == "GROUNDS_MISSTATED"
    assert harness.contract.get_grounds(review_id)[0]["outcome"] \
        == "NOT_IN_NOTICE"
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["GROUNDS_MISSTATED"] == 1


def test_an_unclear_reading_is_inconclusive_and_retryable(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42,
             supported="UNCLEAR"))
    assert verdict == "INCONCLUSIVE"
    review = harness.contract.get_review(review_id)
    assert review["status"] == "RETRYABLE"
    assert review["rounds_used"] == 1
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    assert harness.contract.freshness(review_id, TODAY_DATE) == "UNKNOWN"
    # Nothing was counted: an unsettled review is not a clause's record.
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 4.2")["total"] == 0
    assert harness.contract.get_stats()["resolved"] == 0
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    harness.mock_panel(harness.panel_json([harness.row(
        clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES")]))
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_review(review_id) == "DENIAL_SUPPORTED"
    review = harness.contract.get_review(review_id)
    assert review["status"] == "RESOLVED"
    assert review["rounds_used"] == 2
    assert harness.contract.get_receipt(review_id, 1) != ""
    assert harness.contract.get_receipt(review_id, 2) != ""
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 4.2")["SUPPORTED"] == 1


def test_rounds_run_out_and_the_review_settles_unsettled(ready):
    harness, clause_set_id = ready
    review_id, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42,
             supported="UNCLEAR"))
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_review(review_id) == "INCONCLUSIVE"
    assert harness.contract.review_status(review_id) == "RETRYABLE"
    assert harness.contract.retry_review(review_id) == "INCONCLUSIVE"
    review = harness.contract.get_review(review_id)
    assert review["rounds_used"] == 3
    assert review["status"] == "RESOLVED"
    assert review["verdict"] == "INCONCLUSIVE"
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.retry_review(review_id)
    # An exhausted review counts as resolved but adds nothing to the record
    # of a clause: nothing was decided about that clause.
    assert harness.contract.get_stats()["resolved"] == 1
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 4.2")["total"] == 1
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 4.2")["UNDECIDED"] == 1
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_SUPPORTED"] == 0


def test_an_unreachable_notice_is_not_a_finding(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_UNOCCUPIED, status=404, body="not found")
    review_id = harness.open_review(clause_set_id)
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    review = harness.contract.get_review(review_id)
    assert review["status"] == "RETRYABLE"
    assert review["notice_status"] == "UNAVAILABLE"
    assert review["policy_status"] == "EXAMINED"
    assert review["panel_state"] == "SKIPPED"
    assert harness.contract.get_grounds(review_id)[0]["outcome"] == "UNDECIDED"
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is False
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    harness.mock_panel(harness.panel_json([harness.row(
        clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="NO")]))
    harness.vm.sender = harness.stranger
    assert harness.contract.retry_review(review_id) == "DENIAL_UNSUPPORTED"


def test_a_substituted_document_is_not_the_document(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_UNOCCUPIED,
                     body=doc_text(NOTICE_UNOCCUPIED) + "\nedited later\n")
    review_id = harness.open_review(clause_set_id)
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    assert harness.contract.get_review(review_id)["notice_status"] \
        == "HASH_MISMATCH"


def test_an_oversized_document_is_refused_before_it_is_read(ready):
    harness, clause_set_id = ready
    oversized = "x" * 200001
    harness.mock_doc(NOTICE_UNOCCUPIED, body=oversized)
    review_id = harness.open_review(clause_set_id,
                                    notice_sha=sha_of(oversized))
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    assert harness.contract.get_review(review_id)["notice_status"] \
        == "TOO_LARGE"
    assert harness.contract.get_review(review_id)["panel_state"] == "SKIPPED"


def test_an_empty_document_is_not_a_finding(ready):
    harness, clause_set_id = ready
    blank = "   \n  "
    harness.mock_doc(NOTICE_UNOCCUPIED, body=blank)
    review_id = harness.open_review(clause_set_id, notice_sha=sha_of(blank))
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    assert harness.contract.get_review(review_id)["notice_status"] \
        == "UNREADABLE"


def test_an_unreachable_policy_document_is_not_a_finding(harness):
    clause_set_id = harness.register()
    harness.mock_doc(POLICY, status=503, body="unavailable")
    harness.mock_doc(NOTICE_UNOCCUPIED)
    review_id = harness.open_review(clause_set_id)
    assert harness.resolve(review_id) == "RECORD_UNAVAILABLE"
    review = harness.contract.get_review(review_id)
    assert review["policy_status"] == "UNAVAILABLE"
    assert review["notice_status"] == "EXAMINED"


def test_a_notice_that_addresses_its_reader_cannot_be_upheld(ready):
    harness, clause_set_id = ready
    review_id, verdict = _resolve_one(
        harness, clause_set_id, NOTICE_DIRECTED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_DIR,
             supported="YES"))
    # Every ground was read as supported, and the verdict is still not
    # DENIAL_SUPPORTED: the notice carries instructions to its reader.
    assert verdict == "INCONCLUSIVE"
    review = harness.contract.get_review(review_id)
    assert review["directed_text_hits"] >= 3
    assert review["status"] == "RETRYABLE"
    assert harness.contract.get_grounds(review_id)[0]["outcome"] == "SUPPORTED"
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False


def test_precedence_across_several_grounds(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_JEWELLERY)
    review_id = harness.open_review(
        clause_set_id, notice=NOTICE_JEWELLERY,
        clause_refs=["Clause 5.4", "Clause 3.3"],
        grounds=JEWELLERY_GROUND + LATE_GROUND)
    harness.mock_panel(harness.panel_json([
        harness.row(index=0, clause_quote=CLAUSE_54, notice_quote=NOTICE_54,
                    supported="YES", exceeded=True),
        harness.row(index=1, clause_quote=CLAUSE_33, notice_quote=NOTICE_54,
                    supported="NO"),
    ]))
    # One overbroad ground and one unsupported ground: the stronger defect
    # names the verdict.
    assert harness.resolve(review_id) == "DENIAL_UNSUPPORTED"
    outcomes = [row["outcome"]
                for row in harness.contract.get_grounds(review_id)]
    assert outcomes == ["OVERBROAD", "UNSUPPORTED"]
    outcome = harness.contract.review_outcome(review_id, TODAY_DATE)
    assert outcome["grounds_failing"] == 2
    assert outcome["grounds_supported"] == 0
    # Each clause keeps its own record even though the review has one verdict.
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 5.4")["OVERBROAD"] == 1
    assert harness.contract.clause_record(clause_set_id, 1,
                                          "Clause 3.3")["UNSUPPORTED"] == 1


def test_a_misstated_ground_outranks_a_miscited_clause(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_FLOOD)
    review_id = harness.open_review(
        clause_set_id, notice=NOTICE_FLOOD,
        clause_refs=["Clause 9.4", "Clause 8.5"],
        grounds=FLOOD_GROUND + ["the damage was gradual wear and tear"])
    harness.mock_panel(harness.panel_json([
        harness.row(index=0, located=False, clause_quote="",
                    notice_quote=NOTICE_94, supported="UNCLEAR"),
        harness.row(index=1, clause_quote=quote_from(
            POLICY, "The insurer does not cover damage that is the result"),
            stated=False, notice_quote="", supported="UNCLEAR"),
    ]))
    assert harness.resolve(review_id) == "GROUNDS_MISSTATED"


def test_an_unsupported_ground_outranks_an_undecided_one(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_LATE)
    review_id = harness.open_review(
        clause_set_id, notice=NOTICE_LATE,
        clause_refs=["Clause 3.3", "Clause 6.1"],
        grounds=LATE_GROUND + ["the insured failed to take reasonable care"])
    harness.mock_panel(harness.panel_json([
        harness.row(index=0, clause_quote=CLAUSE_33, notice_quote=NOTICE_33,
                    supported="NO"),
        harness.row(index=1, clause_quote=quote_from(
            POLICY, "The insured must take reasonable care"),
            notice_quote=NOTICE_33, supported="UNCLEAR"),
    ]))
    assert harness.resolve(review_id) == "DENIAL_UNSUPPORTED"


def test_every_ground_must_stand_for_a_denial_to_stand(ready):
    harness, clause_set_id = ready
    harness.mock_doc(NOTICE_JEWELLERY)
    review_id = harness.open_review(
        clause_set_id, notice=NOTICE_JEWELLERY,
        clause_refs=["Clause 5.4", "Clause 3.3"],
        grounds=JEWELLERY_GROUND + LATE_GROUND)
    harness.mock_panel(harness.panel_json([
        harness.row(index=0, clause_quote=CLAUSE_54, notice_quote=NOTICE_54,
                    supported="YES"),
        harness.row(index=1, clause_quote=CLAUSE_33, notice_quote=NOTICE_54,
                    supported="YES"),
    ]))
    assert harness.resolve(review_id) == "DENIAL_SUPPORTED"
    assert harness.contract.review_outcome(
        review_id, TODAY_DATE)["grounds_supported"] == 2


def test_a_resolved_review_is_terminal(ready):
    harness, clause_set_id = ready
    review_id, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES"))
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.resolve_review(review_id)
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.retry_review(review_id)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("illegal transition from RESOLVED"):
        harness.contract.withdraw_review(review_id)
    # The counter did not move a second time.
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_SUPPORTED"] == 1


def test_an_open_review_cannot_be_retried(ready):
    harness, clause_set_id = ready
    review_id = harness.open_review(clause_set_id)
    with harness.vm.expect_revert("illegal transition from OPEN"):
        harness.contract.retry_review(review_id)


def test_the_receipt_is_the_ratified_payload(ready):
    harness, clause_set_id = ready
    review_id, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES"))
    receipt = json.loads(harness.contract.get_receipt(review_id, 1))
    assert receipt["schema"] == "claimcourt/1"
    assert receipt["review_id"] == review_id
    assert receipt["round"] == 1
    assert receipt["policy_sha256"] == doc_sha(POLICY)
    assert receipt["notice_sha256"] == doc_sha(NOTICE_UNOCCUPIED)
    assert receipt["panel_state"] == "READ"
    assert receipt["grounds"][0]["outcome"] == "SUPPORTED"
    assert receipt["literal"][0]["clause_ref_literal"] is True
    assert receipt["definition_hash"] == harness.contract.definition_hash(
        clause_set_id, 1)


def test_a_verdict_goes_stale_after_its_window(harness):
    clause_set_id = harness.register(window=2)
    harness.mock_doc(POLICY)
    review_id, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES"))
    assert harness.contract.freshness(review_id, "2026-10-19") == "RELIABLE"
    assert harness.contract.freshness(review_id, "2026-10-20") == "STALE"
    assert harness.contract.is_fresh(review_id, "2026-10-20") is False
    assert harness.contract.is_consumable(review_id, "2026-10-20") is False
    assert harness.contract.is_denial_supported(review_id,
                                                "2026-10-20") is False
    # A date before the reading, or a date that is not a date, is unknown -
    # never fresh.
    assert harness.contract.freshness(review_id, "2026-10-01") == "UNKNOWN"
    assert harness.contract.freshness(review_id, "not-a-date") == "UNKNOWN"
    assert harness.contract.freshness(review_id, "2026-13-01") == "UNKNOWN"


def test_revoking_the_version_blocks_its_reviews(ready):
    harness, clause_set_id = ready
    review_id, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES"))
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is True
    harness.vm.sender = harness.insurer
    harness.contract.revoke_clause_version(clause_set_id, 1)
    assert harness.contract.freshness(review_id, TODAY_DATE) == "BLOCKED"
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    # The verdict itself is not rewritten: the record stays readable.
    assert harness.contract.review_verdict(review_id) == "DENIAL_SUPPORTED"
    assert harness.contract.clause_set_record(
        clause_set_id, 1)["DENIAL_SUPPORTED"] == 1


def test_a_reissued_notice_gets_its_own_review_with_lineage(ready):
    harness, clause_set_id = ready
    first, _ = _resolve_one(
        harness, clause_set_id, NOTICE_JEWELLERY, ["Clause 5.4"],
        JEWELLERY_GROUND,
        dict(clause_quote=CLAUSE_54, notice_quote=NOTICE_54, supported="YES",
             exceeded=True))
    harness.mock_doc(NOTICE_UNOCCUPIED)
    harness.vm.sender = harness.claimant
    second = harness.contract.supersede_review(
        first, url_for(NOTICE_UNOCCUPIED), doc_sha(NOTICE_UNOCCUPIED),
        ["Clause 4.2"],
        ["the insured address was left unoccupied for more than sixty days"])
    assert harness.contract.get_review(first)["superseded_by"] == second
    new_review = harness.contract.get_review(second)
    assert new_review["supersedes"] == first
    assert new_review["status"] == "OPEN"
    assert new_review["claim_reference"] == "SYN-TEST"
    harness.clear()
    harness.mock_doc(POLICY)
    harness.mock_doc(NOTICE_UNOCCUPIED)
    harness.mock_panel(harness.panel_json([harness.row(
        clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES")]))
    assert harness.resolve(second) == "DENIAL_SUPPORTED"
    # The superseded review keeps its own verdict and its own place in the
    # clause record; nothing is rewritten by the replacement.
    assert harness.contract.review_verdict(first) == "DENIAL_OVERBROAD"
    summary = harness.contract.clause_set_record(clause_set_id, 1)
    assert summary["DENIAL_OVERBROAD"] == 1
    assert summary["DENIAL_SUPPORTED"] == 1


def test_only_a_resolved_review_can_be_superseded_and_only_once(ready):
    harness, clause_set_id = ready
    open_review = harness.open_review(clause_set_id)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("only a resolved review"):
        harness.contract.supersede_review(
            open_review, url_for(NOTICE_LATE), doc_sha(NOTICE_LATE),
            ["Clause 3.3"], LATE_GROUND)
    harness.vm.sender = harness.claimant
    harness.contract.withdraw_review(open_review)
    first, _ = _resolve_one(
        harness, clause_set_id, NOTICE_UNOCCUPIED, ["Clause 4.2"], None,
        dict(clause_quote=CLAUSE_42, notice_quote=NOTICE_42, supported="YES"))
    harness.vm.sender = harness.claimant
    second = harness.contract.supersede_review(
        first, url_for(NOTICE_LATE), doc_sha(NOTICE_LATE), ["Clause 3.3"],
        LATE_GROUND)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("already superseded by " + second):
        harness.contract.supersede_review(
            first, url_for(NOTICE_FLOOD), doc_sha(NOTICE_FLOOD),
            ["Clause 9.4"], FLOOD_GROUND)
