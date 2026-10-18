"""Deterministic lifecycle: who may do what, against which policy version,
in what order, with which evidence, and by when."""

import json

import pytest

from conftest import (CROP_DEFINITION, POLICY_CROP, POLICY_PROPERTY,
                      PROPERTY_DEFINITION, STORM_EVIDENCE, STORM_INCIDENT,
                      STORM_INVOICE, STORM_REPORT, TODAY_DATE, doc_sha,
                      hexaddr, url_for)


def _definition(**changes):
    definition = json.loads(json.dumps(PROPERTY_DEFINITION))
    definition.update(changes)
    return definition


def test_config_is_self_describing(harness):
    config = harness.contract.get_config()
    assert config["schema"] == "claimcourt/1"
    assert config["verdicts"] == ["COVERAGE_SUPPORTED",
                                  "COVERAGE_NOT_ESTABLISHED",
                                  "EXCLUSION_APPLIES",
                                  "FRAUD_INDICATORS_FOUND", "INCONCLUSIVE",
                                  "EVIDENCE_UNAVAILABLE", "CANCELLED"]
    assert "EVIDENCE_CONTRADICTORY" in config["evidence_statuses"]
    assert config["max_evidence"] == 6
    assert config["max_rounds"] == 3
    assert "CANCELLED" not in config["consumable_verdicts"]


def test_registering_a_policy_freezes_and_hashes_it(harness):
    policy_id = harness.register()
    record = harness.contract.get_policy(policy_id, 1)
    assert record["policy_id"] == policy_id
    assert record["owner"] == hexaddr(harness.insurer)
    assert record["policy_version"] == 1
    assert record["spec_version"] == "claimcourt/1"
    assert record["policy_sha256"] == doc_sha(POLICY_PROPERTY)
    assert len(record["policy_hash"]) == 64
    assert record["revoked"] is False
    assert record["is_current_version"] is True
    assert record["review_window_days"] == 365
    assert [c["ref"] for c in record["coverage_conditions"]] == ["C1", "C2",
                                                                "C3"]
    assert record["coverage_conditions"][0]["covered_event"] is True
    assert record["coverage_conditions"][1]["covered_event"] is False
    assert [x["ref"] for x in record["exclusions"]] == ["X1", "X2"]
    assert record["fraud_question"] == ""
    assert record["trigger"] == ""
    assert harness.contract.get_stats()["policies"] == 1


def test_the_policy_hash_covers_the_terms_not_just_the_document(harness):
    first = harness.register()
    changed = _definition()
    changed["coverage_conditions"][1]["text"] = (
        "The loss was reported to the insurer within seven days of the "
        "insured becoming aware of it.")
    second = harness.register(changed)
    assert harness.contract.get_policy(first, 1)["policy_sha256"] \
        == harness.contract.get_policy(second, 1)["policy_sha256"]
    # Same wording document, different conditions: different policy hash.
    assert harness.contract.get_policy(first, 1)["policy_hash"] \
        != harness.contract.get_policy(second, 1)["policy_hash"]


def test_a_parametric_policy_records_its_trigger(harness):
    policy_id = harness.register(CROP_DEFINITION, policy=POLICY_CROP,
                                 coverage_type="parametric drought")
    trigger = json.loads(harness.contract.get_policy(policy_id, 1)["trigger"])
    assert trigger["rule"] == "AT_MOST"
    assert trigger["threshold"] == 220
    assert trigger["unit"] == "millimetres"
    assert trigger["window_start"] == "2026-06-01"
    assert trigger["window_end"] == "2026-09-30"


@pytest.mark.parametrize("changes,reason", [
    ({"coverage_conditions": []}, "at least one coverage condition"),
    ({"coverage_conditions": [{"ref": "C" + str(n), "text": "x" * 20}
                              for n in range(7)]},
     "at most 6 coverage conditions"),
    ({"coverage_conditions": [{"ref": "", "text": "a condition text here"}]},
     "needs a reference"),
    ({"coverage_conditions": [{"ref": "C1", "text": "short"}]},
     "needs its text"),
    ({"coverage_conditions": [{"ref": "C1", "text": "a condition text here"},
                              {"ref": "C1", "text": "another text here"}]},
     "duplicate condition reference"),
    ({"coverage_conditions": [{"ref": "C1", "text": "a condition text here",
                               "covered_event": "yes"}]},
     "covered_event must be true or false"),
    ({"exclusions": [{"ref": "X1", "text": "short"}]}, "needs its text"),
    ({"exclusions": [{"ref": "C1", "text": "a clashing reference here"}]},
     "duplicate reference"),
    ({"review_window_days": 0}, "review window must be between"),
    ({"review_window_days": 4000}, "review window must be between"),
    ({"review_window_days": "365"}, "must be a whole number"),
])
def test_a_policy_definition_is_admitted_deterministically(harness, changes,
                                                           reason):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert(reason):
        harness.contract.register_policy(
            url_for(POLICY_PROPERTY), doc_sha(POLICY_PROPERTY),
            "small commercial property", json.dumps(_definition(**changes)))


@pytest.mark.parametrize("trigger,reason", [
    ({"measure": "", "unit": "mm", "rule": "AT_MOST", "threshold": 10,
      "window_start": "2026-06-01", "window_end": "2026-09-30"},
     "needs a measure and a unit"),
    ({"measure": "cumulative rainfall", "unit": "mm", "rule": "ABOVE",
      "threshold": 10, "window_start": "2026-06-01",
      "window_end": "2026-09-30"}, "trigger rule must be one of"),
    ({"measure": "cumulative rainfall", "unit": "mm", "rule": "AT_MOST",
      "threshold": -1, "window_start": "2026-06-01",
      "window_end": "2026-09-30"}, "threshold must be a whole number"),
    ({"measure": "cumulative rainfall", "unit": "mm", "rule": "AT_MOST",
      "threshold": True, "window_start": "2026-06-01",
      "window_end": "2026-09-30"}, "threshold must be a whole number"),
    ({"measure": "cumulative rainfall", "unit": "mm", "rule": "AT_MOST",
      "threshold": 10, "window_start": "not-a-date",
      "window_end": "2026-09-30"}, "needs an insured window"),
    ({"measure": "cumulative rainfall", "unit": "mm", "rule": "AT_MOST",
      "threshold": 10, "window_start": "2026-09-30",
      "window_end": "2026-06-01"}, "window ends before it starts"),
])
def test_a_trigger_is_admitted_deterministically(harness, trigger, reason):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert(reason):
        harness.contract.register_policy(
            url_for(POLICY_CROP), doc_sha(POLICY_CROP), "parametric drought",
            json.dumps(_definition(trigger=trigger)))


def test_a_malformed_definition_is_refused(harness):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("not valid json"):
        harness.contract.register_policy(
            url_for(POLICY_PROPERTY), doc_sha(POLICY_PROPERTY), "property",
            "{not json")
    with harness.vm.expect_revert("must be an object"):
        harness.contract.register_policy(
            url_for(POLICY_PROPERTY), doc_sha(POLICY_PROPERTY), "property",
            "[]")


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
    ("https://", "URL_HAS_NO_HOST"),
    ("", "URL_BLANK_OR_PADDED"),
])
def test_document_locations_are_admitted_deterministically(harness, url,
                                                           reason):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert(reason):
        harness.contract.register_policy(url, "c" * 64, "property",
                                         json.dumps(PROPERTY_DEFINITION))


@pytest.mark.parametrize("digest", ["", "abc", "A" * 64, "g" * 64, "0" * 63])
def test_a_document_hash_must_be_lowercase_hex(harness, digest):
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("64 lowercase hex characters"):
        harness.contract.register_policy(url_for(POLICY_PROPERTY), digest,
                                         "property",
                                         json.dumps(PROPERTY_DEFINITION))


def test_only_the_owner_publishes_or_revokes(harness):
    policy_id = harness.register()
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the policy owner"):
        harness.contract.publish_policy_version(
            policy_id, url_for(POLICY_PROPERTY), "b" * 64,
            json.dumps(PROPERTY_DEFINITION))
    with harness.vm.expect_revert("only the policy owner"):
        harness.contract.revoke_policy_version(policy_id, 1)
    with harness.vm.expect_revert("only the policy owner"):
        harness.contract.open_claim_challenge(
            policy_id, "Does this claim satisfy the conditions of cover?",
            json.dumps(["incident_report"]), "2026-12-31")


def test_a_new_version_does_not_touch_an_open_challenge(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    first_hash = harness.contract.get_policy_hash(claim_id)
    harness.vm.sender = harness.insurer
    version = harness.contract.publish_policy_version(
        policy_id, url_for(POLICY_PROPERTY), "b" * 64,
        json.dumps(_definition(review_window_days=30)))
    assert version == 2
    assert harness.contract.get_policy_version(claim_id) == 1
    assert harness.contract.get_policy_hash(claim_id) == first_hash
    assert harness.contract.get_policy(policy_id, 1)["is_current_version"] \
        is False
    assert harness.contract.get_policy(policy_id, 2)["review_window_days"] \
        == 30


def test_a_revoked_version_takes_no_new_claims(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.vm.sender = harness.insurer
    harness.contract.revoke_policy_version(policy_id, 1)
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("already revoked"):
        harness.contract.revoke_policy_version(policy_id, 1)
    with harness.vm.expect_revert("the active policy version is revoked"):
        harness.open_challenge(policy_id)
    with harness.vm.expect_revert("the bound policy version is revoked"):
        harness.submit(claim_id)


def test_a_challenge_states_the_question_and_what_it_needs(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(
        policy_id, required=["incident_report", "invoice"],
        question="Does this claim satisfy the conditions of cover for the "
                 "damage claimed, and does any exclusion apply?")
    record = harness.contract.get_claim(claim_id)
    assert record["claim_id"] == claim_id
    assert record["policy_id"] == policy_id
    assert record["policy_version"] == 1
    assert record["spec_version"] == "claimcourt/1"
    assert record["coverage_type"] == "small commercial property"
    assert record["required_evidence"] == ["incident_report", "invoice"]
    assert record["claim_deadline"] == "2026-12-31"
    assert record["opened_on"] == TODAY_DATE
    assert record["status"] == "OPEN"
    assert record["submissions"] == 0
    assert [c["ref"] for c in record["coverage_conditions"]] == ["C1", "C2",
                                                                "C3"]
    assert [x["ref"] for x in record["exclusions"]] == ["X1", "X2"]
    assert harness.contract.get_claim_status(claim_id) == "OPEN"
    assert harness.contract.get_policy_hash(claim_id) \
        == harness.contract.get_policy(policy_id, 1)["policy_hash"]


@pytest.mark.parametrize("required,deadline,question,reason", [
    ([], "2026-12-31", None, "at least one kind of evidence"),
    (["a", "b", "c", "d", "e", "f", "g"], "2026-12-31", None,
     "at most 6 required kinds"),
    (["incident_report", "incident_report"], "2026-12-31", None,
     "duplicate required evidence kind"),
    (["x"], "2026-12-31", None, "required evidence kind is empty"),
    (["incident_report"], "not-a-date", None, "must be an ISO date"),
    (["incident_report"], "2026-01-01", None, "deadline has already passed"),
    (["incident_report"], "2026-12-31", "too short", "a decision question"),
])
def test_a_challenge_is_admitted_deterministically(harness, required,
                                                   deadline, question,
                                                   reason):
    policy_id = harness.register()
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert(reason):
        harness.contract.open_claim_challenge(
            policy_id,
            question or "Does this claim satisfy the conditions of cover?",
            json.dumps(required), deadline)


def test_a_cancelled_challenge_takes_no_submissions(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the policy owner"):
        harness.contract.cancel_claim_challenge(claim_id)
    harness.vm.sender = harness.insurer
    harness.contract.cancel_claim_challenge(claim_id)
    assert harness.contract.get_claim_status(claim_id) == "CANCELLED"
    with harness.vm.expect_revert("that challenge is cancelled"):
        harness.submit(claim_id)
    harness.vm.sender = harness.insurer
    with harness.vm.expect_revert("illegal transition from CANCELLED"):
        harness.contract.cancel_claim_challenge(claim_id)


def test_a_submission_binds_the_version_and_every_document(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    submission_id = harness.submit(claim_id)
    record = harness.contract.get_submission(submission_id)
    assert record["claim_id"] == claim_id
    assert record["policy_id"] == policy_id
    assert record["policy_version"] == 1
    assert record["policy_hash"] == harness.contract.get_policy_hash(claim_id)
    assert record["claimant"] == hexaddr(harness.claimant)
    assert record["claimant_reference"] == "SYN-2041"
    assert record["incident_date"] == "2026-03-03"
    assert record["claimed_loss_category"] == "contents"
    assert record["claimed_amount_band"] == "1000-5000"
    assert record["submitted_at"] == TODAY_DATE
    assert record["status"] == "PENDING"
    assert record["verdict"] == "PENDING"
    assert len(record["evidence_digest"]) == 64
    assert [item["evidence_id"] for item in record["evidence_refs"]] \
        == ["E1", "E2", "E3"]
    assert [item["kind"] for item in record["evidence_refs"]] \
        == ["incident_report", "invoice", "weather_record"]
    assert record["evidence_refs"][0]["sha256"] == doc_sha(STORM_REPORT)
    assert harness.contract.list_submissions(claim_id, 0, 50) \
        == [submission_id]
    assert harness.contract.get_claim(claim_id)["submissions"] == 1
    assert harness.contract.evidence_first_seen(doc_sha(STORM_REPORT)) \
        == submission_id


def test_a_claim_must_carry_every_kind_the_challenge_requires(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(
        policy_id, required=["incident_report", "invoice", "photograph"])
    with harness.vm.expect_revert("requires evidence of kind photograph"):
        harness.submit(claim_id)


def test_a_claim_after_the_deadline_is_refused(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id, deadline="2026-10-18")
    harness.set_clock("2026-10-19T09:00:00.000+00:00")
    with harness.vm.expect_revert("the claim deadline has passed"):
        harness.submit(claim_id)
    # One day earlier the same claim is admitted, so the rule is the date
    # and not something else about the submission.
    harness.set_clock("2026-10-18T09:00:00.000+00:00")
    assert harness.submit(claim_id) == "sub-1"


@pytest.mark.parametrize("incident,reason", [
    ({"incident_summary": "short", "incident_date": "2026-03-03"},
     "incident summary is required"),
    ({"incident_summary": "a summary long enough to count",
      "incident_date": "not-a-date"}, "must be an ISO date"),
    ({"incident_summary": "a summary long enough to count",
      "incident_date": "2027-01-01"}, "incident date is in the future"),
])
def test_an_incident_record_is_admitted_deterministically(harness, incident,
                                                          reason):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    with harness.vm.expect_revert(reason):
        harness.submit(claim_id, incident=incident)


def test_the_incident_record_must_be_json(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.vm.sender = harness.claimant
    with harness.vm.expect_revert("not valid json"):
        harness.contract.submit_claim(claim_id, "SYN-1", "{oops",
                                      json.dumps([]))


def test_evidence_is_admitted_deterministically(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id, required=["incident_report"])
    with harness.vm.expect_revert("at least one evidence document"):
        harness.submit(claim_id, evidence=[])
    too_many = [{"evidence_id": "E" + str(n), "kind": "incident_report",
                 "name": STORM_REPORT} for n in range(7)]
    with harness.vm.expect_revert("at most 6 evidence documents"):
        harness.submit(claim_id, evidence=too_many)
    with harness.vm.expect_revert("duplicate evidence id"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "incident_report",
             "name": STORM_REPORT},
            {"evidence_id": "E1", "kind": "invoice", "name": STORM_INVOICE}])
    with harness.vm.expect_revert("the same document is listed twice"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "incident_report",
             "name": STORM_REPORT},
            {"evidence_id": "E2", "kind": "invoice", "name": STORM_REPORT}])
    with harness.vm.expect_revert("needs a kind"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "", "name": STORM_REPORT}])
    with harness.vm.expect_revert("evidence url rejected"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "incident_report",
             "url": "http://example.com/report.txt",
             "sha256": doc_sha(STORM_REPORT)}])
    with harness.vm.expect_revert("evidence sha256 must be"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "incident_report",
             "url": url_for(STORM_REPORT), "sha256": "nope"}])


def test_the_policy_wording_is_not_claim_evidence(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id, required=["incident_report"])
    with harness.vm.expect_revert("the policy wording is not claim evidence"):
        harness.submit(claim_id, evidence=[
            {"evidence_id": "E1", "kind": "incident_report",
             "name": POLICY_PROPERTY}])


def test_submissions_are_independent_records(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    first = harness.submit(claim_id, reference="SYN-A")
    second = harness.submit(claim_id, reference="SYN-B")
    assert first != second
    assert harness.contract.get_submission(second)["claimant_reference"] \
        == "SYN-B"
    assert harness.contract.list_submissions(claim_id, 1, 50) == [second]
    assert harness.contract.list_submissions(claim_id, 0, 1) == [first]
    assert harness.contract.get_stats()["submissions"] == 2
    # The registry remembers which claim first committed a document, and
    # that is a fact, not a finding.
    assert harness.contract.evidence_first_seen(doc_sha(STORM_REPORT)) \
        == first
    assert policy_id == "pol-1"


def test_a_pending_claim_decides_nothing(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    submission_id = harness.submit(claim_id)
    assert harness.contract.get_verdict(submission_id)["verdict"] == "PENDING"
    assert harness.contract.get_evidence_status(submission_id) == ""
    assert harness.contract.is_coverage_supported(submission_id,
                                                  TODAY_DATE) is False
    assert harness.contract.is_consumable(submission_id, TODAY_DATE) is False
    assert harness.contract.freshness(submission_id, TODAY_DATE) == "UNKNOWN"
    assert harness.contract.get_receipt(submission_id, 1) == ""
    findings = harness.contract.get_findings(submission_id)
    assert [row["finding"] for row in findings["conditions"]] \
        == ["NOT_ASSESSED"] * 3
    assert [row["finding"] for row in findings["exclusions"]] \
        == ["NOT_ASSESSED"] * 2
    with harness.vm.expect_revert("illegal transition from PENDING"):
        harness.contract.retry_submission(submission_id)
    assert harness.contract.policy_record(policy_id, 1)["total"] == 0


def test_unknown_identifiers_are_rejected(harness):
    harness.register()
    with harness.vm.expect_revert("no such policy"):
        harness.open_challenge("pol-404")
    with harness.vm.expect_revert("no such policy version"):
        harness.contract.get_policy("pol-1", 9)
    with harness.vm.expect_revert("no such claim challenge"):
        harness.contract.get_claim("clm-404")
    with harness.vm.expect_revert("no such submission"):
        harness.contract.get_submission("sub-404")
    with harness.vm.expect_revert("no such submission"):
        harness.contract.resolve_submission("sub-404")
    assert harness.contract.evidence_first_seen("f" * 64) == ""


def test_long_text_is_truncated_not_rejected(harness):
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    submission_id = harness.submit(
        claim_id, reference="SYN-" + "x" * 200,
        incident=dict(STORM_INCIDENT,
                      incident_summary="a storm damaged the stockroom "
                                       + "y" * 900))
    record = harness.contract.get_submission(submission_id)
    assert len(record["claimant_reference"]) == 48
    assert len(record["incident_summary"]) == 600
    assert STORM_EVIDENCE[0]["kind"] == "incident_report"
