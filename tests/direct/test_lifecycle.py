"""Deterministic lifecycle: who may do what, to which version, in what
order, and what a bound document is allowed to be."""

import pytest

from conftest import (NOTICE_FLOOD, NOTICE_LATE, NOTICE_UNOCCUPIED, POLICY,
                      TODAY_DATE, doc_sha, hexaddr, url_for)


def test_config_is_self_describing(harness):
    config = harness.contract.get_config()
    assert config["schema"] == "claimcourt/1"
    assert config["max_grounds"] == 6
    assert "DENIAL_SUPPORTED" in config["verdicts"]
    assert "WITHDRAWN" in config["terminal_verdicts"]
    assert config["retryable_verdicts"] == ["INCONCLUSIVE",
                                            "RECORD_UNAVAILABLE"]


def test_registration_stores_a_hashed_definition(harness):
    clause_set_id = harness.register()
    record = harness.contract.get_clause_set(clause_set_id, 1)
    assert record["clause_set_id"] == clause_set_id
    assert record["version"] == 1
    assert record["owner"] == hexaddr(harness.insurer)
    assert record["policy_sha256"] == doc_sha(POLICY)
    assert len(record["definition_hash"]) == 64
    assert record["revoked"] is False
    assert record["is_current_version"] is True
    assert record["review_window_days"] == 365
    assert harness.contract.clause_set_head(clause_set_id) == 1
    assert harness.contract.get_stats()["clause_sets"] == 1


def test_definition_hash_covers_the_document_and_the_version(harness):
    first = harness.register()
    second = harness.register()
    assert harness.contract.definition_hash(first, 1) \
        != harness.contract.definition_hash(second, 1)


def test_only_the_owner_publishes_or_revokes(harness):
    clause_set_id = harness.register()
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the clause set owner"):
        harness.contract.publish_clause_version(
            clause_set_id, url_for("policy-household-v2.txt"), "a" * 64)
    with harness.vm.expect_revert("only the clause set owner"):
        harness.contract.revoke_clause_version(clause_set_id, 1)


def test_a_new_version_does_not_touch_an_open_review(harness):
    clause_set_id = harness.register()
    review_id = harness.open_review(clause_set_id)
    first_hash = harness.contract.get_review(review_id)["definition_hash"]
    harness.vm.sender = harness.insurer
    version = harness.contract.publish_clause_version(
        clause_set_id, url_for("policy-household-v2.txt"), "b" * 64)
    assert version == 2
    assert harness.contract.clause_set_head(clause_set_id) == 2
    review = harness.contract.get_review(review_id)
    assert review["version"] == 1
    assert review["definition_hash"] == first_hash
    assert harness.contract.get_clause_set(clause_set_id, 1)[
        "is_current_version"] is False


def test_a_version_cannot_be_republished_with_the_same_bytes(harness):
    clause_set_id = harness.register()
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("that is the current version's document"):
        harness.contract.publish_clause_version(clause_set_id,
                                                url_for(POLICY),
                                                doc_sha(POLICY))


def test_a_review_cannot_be_opened_on_a_revoked_version(harness):
    clause_set_id = harness.register()
    harness.vm.sender = harness.insurer
    harness.contract.revoke_clause_version(clause_set_id, 1)
    with harness.vm.expect_revert("the active clause version is revoked"):
        harness.open_review(clause_set_id)
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("already revoked"):
        harness.contract.revoke_clause_version(clause_set_id, 1)


def test_anyone_may_open_a_review(harness):
    clause_set_id = harness.register()
    review_id = harness.open_review(clause_set_id, sender=harness.stranger)
    review = harness.contract.get_review(review_id)
    assert review["opener"] == hexaddr(harness.stranger)
    assert review["status"] == "OPEN"
    assert review["verdict"] == "PENDING"
    assert review["opened_on"] == TODAY_DATE
    assert review["rounds_used"] == 0
    assert review["ground_count"] == 1
    assert harness.contract.list_reviews(clause_set_id, 1, 0, 50) \
        == [review_id]
    assert harness.contract.notice_under_review(doc_sha(NOTICE_UNOCCUPIED)) \
        == review_id


def test_the_same_notice_is_reviewed_once(harness):
    clause_set_id = harness.register()
    first = harness.open_review(clause_set_id)
    with harness.vm.expect_revert("already under review as " + first):
        harness.open_review(clause_set_id)


def test_a_withdrawn_review_releases_its_notice(harness):
    clause_set_id = harness.register()
    first = harness.open_review(clause_set_id)
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the opener"):
        harness.contract.withdraw_review(first)
    harness.vm.sender = harness.claimant
    harness.contract.withdraw_review(first)
    review = harness.contract.get_review(first)
    assert review["status"] == "WITHDRAWN"
    assert review["verdict"] == "WITHDRAWN"
    assert harness.contract.notice_under_review(
        doc_sha(NOTICE_UNOCCUPIED)) == ""
    second = harness.open_review(clause_set_id)
    assert second != first
    assert harness.contract.is_consumable(first, TODAY_DATE) is False
    assert harness.contract.freshness(first, TODAY_DATE) == "UNKNOWN"


def test_a_withdrawn_review_cannot_be_withdrawn_twice(harness):
    clause_set_id = harness.register()
    review_id = harness.open_review(clause_set_id)
    harness.vm.sender = harness.claimant
    harness.contract.withdraw_review(review_id)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("illegal transition from WITHDRAWN"):
        harness.contract.withdraw_review(review_id)


def test_the_notice_cannot_be_the_policy_document(harness):
    clause_set_id = harness.register()
    with harness.vm.expect_revert("cannot be the policy document"):
        harness.open_review(clause_set_id, notice=POLICY)


def test_unknown_identifiers_are_rejected(harness):
    harness.register()
    with harness.vm.expect_revert("no such clause set"):
        harness.open_review("cs-404")
    with harness.vm.expect_revert("no such clause version"):
        harness.contract.get_clause_set("cs-1", 9)
    with harness.vm.expect_revert("no such review"):
        harness.contract.get_review("rv-404")
    with harness.vm.expect_revert("no such review"):
        harness.contract.resolve_review("rv-404")


@pytest.mark.parametrize("url,reason", [
    ("http://example.com/policy.txt", "URL_NOT_HTTPS"),
    ("https://user:pass@example.com/p.txt", "URL_HAS_CREDENTIALS"),
    ("https://example.com:8443/p.txt", "URL_HAS_EXPLICIT_PORT"),
    ("https://localhost/p.txt", "URL_HOST_IS_LOCAL"),
    ("https://files.localhost/p.txt", "URL_HOST_IS_LOCAL"),
    ("https://intranet.internal/p.txt", "URL_HOST_IS_INTERNAL"),
    ("https://nas.local/p.txt", "URL_HOST_IS_INTERNAL"),
    ("https://127.0.0.1/p.txt", "URL_HOST_IS_PRIVATE_IP"),
    ("https://10.1.2.3/p.txt", "URL_HOST_IS_PRIVATE_IP"),
    ("https://192.168.0.5/p.txt", "URL_HOST_IS_PRIVATE_IP"),
    ("https://172.20.9.9/p.txt", "URL_HOST_IS_PRIVATE_IP"),
    ("https://169.254.1.1/p.txt", "URL_HOST_IS_PRIVATE_IP"),
    ("https://8.8.8.8/p.txt", "URL_HOST_IS_RAW_IP"),
    ("https://example/p.txt", "URL_HOST_HAS_NO_DOT"),
    ("https://ex ample.com/p.txt", "URL_HAS_UNSAFE_CHARACTER"),
    ("https://exa_mple.com/p.txt", "URL_HOST_MALFORMED"),
    ("https://example..com/p.txt", "URL_HOST_MALFORMED"),
    ("https://", "URL_HAS_NO_HOST"),
    ("", "URL_BLANK_OR_PADDED"),
    (" https://example.com/p.txt", "URL_BLANK_OR_PADDED"),
])
def test_document_locations_are_admitted_deterministically(harness, url,
                                                           reason):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert(reason):
        harness.contract.register_clause_set("Synthetic wording", url,
                                             "c" * 64, 0)


def test_a_long_url_is_rejected(harness):
    harness.vm.sender = harness.insurer
    long_url = "https://example.com/" + ("a" * 300)
    with harness.vm.expect_revert("URL_TOO_LONG"):
        harness.contract.register_clause_set("Synthetic wording", long_url,
                                             "c" * 64, 0)


@pytest.mark.parametrize("digest", [
    "", "abc", "A" * 64, "g" * 64, "0" * 63, "0" * 65,
])
def test_a_document_hash_must_be_lowercase_hex(harness, digest):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("64 lowercase hex characters"):
        harness.contract.register_clause_set("Synthetic wording",
                                             url_for(POLICY), digest, 0)


def test_a_label_is_required(harness):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("needs a label"):
        harness.contract.register_clause_set("  ", url_for(POLICY),
                                             doc_sha(POLICY), 0)


@pytest.mark.parametrize("window", [-1, 3651, 100000])
def test_the_review_window_is_bounded(harness, window):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("review window must be between"):
        harness.contract.register_clause_set("Synthetic wording",
                                             url_for(POLICY),
                                             doc_sha(POLICY), window)


def test_grounds_are_bounded_and_paired(harness):
    clause_set_id = harness.register()
    with harness.vm.expect_revert("at least one ground"):
        harness.open_review(clause_set_id, clause_refs=[], grounds=[])
    with harness.vm.expect_revert("one ground text is required per clause"):
        harness.open_review(clause_set_id, clause_refs=["Clause 4.2"],
                            grounds=[])
    with harness.vm.expect_revert("at most 6 grounds"):
        harness.open_review(clause_set_id,
                            clause_refs=["Clause 4.2"] * 7,
                            grounds=["the premises were left unoccupied"] * 7)
    with harness.vm.expect_revert("clause reference is empty"):
        harness.open_review(clause_set_id, clause_refs=[" "],
                            grounds=["the premises were left unoccupied"])
    with harness.vm.expect_revert("must state the reason"):
        harness.open_review(clause_set_id, clause_refs=["Clause 4.2"],
                            grounds=["too short"])
    with harness.vm.expect_revert("duplicate ground"):
        harness.open_review(
            clause_set_id, clause_refs=["Clause 4.2", "Clause 4.2"],
            grounds=["the premises were left unoccupied for sixty days",
                     "the premises were left unoccupied for sixty days"])


def test_long_text_is_truncated_not_rejected(harness):
    clause_set_id = harness.register()
    review_id = harness.open_review(
        clause_set_id, clause_refs=["Clause 4.2" + " x" * 200],
        grounds=["the premises were left unoccupied " + "y" * 900])
    grounds = harness.contract.get_grounds(review_id)
    assert len(grounds[0]["clause_ref"]) == 64
    assert len(grounds[0]["asserted_ground"]) == 400


def test_six_grounds_are_accepted(harness):
    clause_set_id = harness.register()
    refs = ["Clause 2.1", "Clause 3.3", "Clause 4.2", "Clause 5.4",
            "Clause 6.1", "Clause 7.2"]
    grounds = ["ground number " + str(n) + " as the notice states it"
               for n in range(6)]
    review_id = harness.open_review(clause_set_id, clause_refs=refs,
                                    grounds=grounds)
    stored = harness.contract.get_grounds(review_id)
    assert [row["clause_ref"] for row in stored] == refs


def test_reviews_are_independent_records(harness):
    clause_set_id = harness.register()
    first = harness.open_review(clause_set_id)
    second = harness.open_review(clause_set_id, notice=NOTICE_LATE,
                                 clause_refs=["Clause 3.3"],
                                 grounds=["the claim was notified late so "
                                          "the cover ended"],
                                 reference="SYN-0052")
    third = harness.open_review(clause_set_id, notice=NOTICE_FLOOD,
                                clause_refs=["Clause 9.4"],
                                grounds=["the loss was caused by flood or "
                                         "rising groundwater"],
                                reference="SYN-0074")
    assert len({first, second, third}) == 3
    assert harness.contract.get_review(second)["claim_reference"] == "SYN-0052"
    assert harness.contract.list_reviews(clause_set_id, 1, 1, 50) \
        == [second, third]
    assert harness.contract.list_reviews(clause_set_id, 1, 0, 1) == [first]
    assert harness.contract.get_stats()["reviews"] == 3


def test_a_review_is_always_pending_before_it_is_read(harness):
    clause_set_id = harness.register()
    review_id = harness.open_review(clause_set_id)
    assert harness.contract.review_verdict(review_id) == "PENDING"
    assert harness.contract.review_status(review_id) == "OPEN"
    assert harness.contract.is_consumable(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_supported(review_id, TODAY_DATE) is False
    assert harness.contract.is_denial_unsupported(review_id,
                                                  TODAY_DATE) is False
    assert harness.contract.get_receipt(review_id, 1) == ""
    outcome = harness.contract.review_outcome(review_id, TODAY_DATE)
    assert outcome["verdict"] == "PENDING"
    assert outcome["freshness"] == "UNKNOWN"
    assert outcome["consumable"] is False
    assert outcome["grounds_total"] == 1
    assert outcome["grounds_failing"] == 0


def test_an_empty_clause_record_reads_as_zero(harness):
    clause_set_id = harness.register()
    record = harness.contract.clause_record(clause_set_id, 1, "Clause 4.2")
    assert record["total"] == 0
    assert record["SUPPORTED"] == 0
    summary = harness.contract.clause_set_record(clause_set_id, 1)
    assert summary["reviews"] == 0
    assert summary["DENIAL_SUPPORTED"] == 0
