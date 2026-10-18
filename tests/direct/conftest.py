"""Shared harness for the Direct Mode suite.

Only the nondeterministic edges are mocked: the policy fetch, each evidence
fetch, and the panel call. Everything between them - admission, deadlines,
required kinds, hashing, grounding, the trigger comparison, precedence,
storage and the counters - is the contract's own code.
"""

import hashlib
import json
import os
import pathlib
import sys

import pytest

from eth_utils import to_checksum_address

from gltest.direct import VMContext, deploy_contract, create_test_addresses


def hexaddr(account) -> str:
    """The checksummed spelling a contract stores for a test account."""
    return to_checksum_address(bytes(account))


def _tolerate_windows_tempfile_unlink():
    """Work around a Windows-only failure in the Direct Mode loader.

    `gltest` 0.29.2 writes the transaction message to a temp file, binds that
    file to fd 0 with `dup2`, closes its own descriptor and then unlinks the
    path. POSIX allows unlinking a file another descriptor still references;
    Windows does not, so contract loading dies with

        PermissionError: [WinError 32] The process cannot access the file
        because it is being used by another process

    before any contract code runs. This wraps the loader's own helper so that
    one failed cleanup is tolerated - the file is released when the process
    exits - and restores `os.unlink` immediately afterwards.

    It is a test-harness workaround for a host OS behaviour. The contract is
    not involved and not modified, nothing outside the loader's own call is
    affected, and on anything other than Windows this does nothing at all.
    """
    if sys.platform != "win32":
        return
    from gltest.direct import loader

    original = getattr(loader, "_inject_message_to_fd0", None)
    if original is None or getattr(original, "_unlink_tolerated", False):
        return

    def wrapped(vm):
        real_unlink = os.unlink

        def tolerant(path, *args, **kwargs):
            try:
                real_unlink(path, *args, **kwargs)
            except OSError:
                pass

        os.unlink = tolerant
        try:
            return original(vm)
        finally:
            os.unlink = real_unlink

    wrapped._unlink_tolerated = True
    loader._inject_message_to_fd0 = wrapped


_tolerate_windows_tempfile_unlink()


ROOT = pathlib.Path(__file__).resolve().parents[2]

# The suite runs against the committed contract unless a mutation sweep
# points it at a patched copy (scripts/mutate.py).
CONTRACT = pathlib.Path(
    os.environ.get("CLAIMCOURT_CONTRACT",
                   str(ROOT / "contracts" / "claimcourt.py")))
FIXTURES = ROOT / "fixtures"

# Any https host works against a mocked fetch; these are the locations the
# live suite uses, so both suites meet the same admission rules.
BASE = "https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/main/fixtures/"

POLICY_PROPERTY = "policy-property-v1.txt"
POLICY_CROP = "policy-crop-parametric-v1.txt"
STORM_REPORT = "incident-report-storm.txt"
STORM_INVOICE = "repair-invoice-storm.txt"
GRADUAL_REPORT = "assessor-report-gradual.txt"
NO_ENTRY_REPORT = "incident-report-no-forced-entry.txt"
DIRECTED_REPORT = "incident-report-directed.txt"
RAINFALL_RECORD = "rainfall-record-season.txt"
HOLDING_STATEMENT = "holding-statement-groundnut.txt"

TODAY = "2026-10-17T09:30:00.000+00:00"
TODAY_DATE = "2026-10-17"
DEADLINE = "2026-12-31"


def doc_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def doc_text(name: str) -> str:
    return doc_bytes(name).decode("utf-8")


def doc_sha(name: str) -> str:
    return hashlib.sha256(doc_bytes(name)).hexdigest()


def url_for(name: str) -> str:
    return BASE + name


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quote_from(name: str, needle: str, length: int = 90) -> str:
    """A verbatim span of a fixture, flattened the way the contract
    flattens, so a test quotes what the document really says."""
    text = " ".join(doc_text(name).split())
    position = text.find(needle)
    assert position >= 0, "fixture does not contain " + needle
    return text[position:position + length]


# -- the policies the suite uses -------------------------------------------

PROPERTY_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "A covered event under clause 1 occurred at the insured "
                 "premises during the period of insurance and caused the "
                 "damage claimed."},
        {"ref": "C2",
         "text": "The loss was reported to the insurer within thirty days "
                 "of the insured becoming aware of it, and the record shows "
                 "when they became aware."},
        {"ref": "C3",
         "text": "The cost of reinstatement for the items claimed is "
                 "evidenced by an invoice, an estimate or an assessor's "
                 "figure."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The damage is the result of gradual deterioration, wear "
                 "and tear, rot, corrosion or lack of maintenance over "
                 "time, rather than a sudden event."},
        {"ref": "X2",
         "text": "The premises were left unoccupied for more than sixty "
                 "consecutive days immediately before the loss."},
    ],
    "review_window_days": 365,
}

THEFT_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "A covered event under clause 1 occurred at the insured "
                 "premises during the period of insurance and caused the "
                 "loss claimed."},
        {"ref": "C4",
         "text": "For a theft claim there is evidence of forcible and "
                 "violent entry to the premises. Entry by a door or window "
                 "left open or unlocked is not forcible and violent entry."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The loss is the result of gradual deterioration, wear and "
                 "tear or lack of maintenance over time."},
    ],
    "review_window_days": 365,
}

CROP_DEFINITION = {
    "coverage_conditions": [
        {"ref": "C1", "covered_event": True,
         "text": "The claim is made for the holding named in the schedule "
                 "and identifies the station and window the schedule "
                 "names."},
        {"ref": "C2",
         "text": "The claim is supported by the published rainfall record "
                 "for that station and window, as issued by the publishing "
                 "body."},
    ],
    "exclusions": [
        {"ref": "X1",
         "text": "The loss was caused by pests, disease, fire, theft or "
                 "civil disturbance rather than by the measured rainfall "
                 "shortfall."},
    ],
    "trigger": {
        "measure": "cumulative rainfall at the synthetic reference station",
        "unit": "millimetres",
        "rule": "AT_MOST",
        "threshold": 220,
        "window_start": "2026-06-01",
        "window_end": "2026-09-30",
    },
    "review_window_days": 365,
}

FRAUD_DEFINITION = json.loads(json.dumps(PROPERTY_DEFINITION))
FRAUD_DEFINITION["fraud_question"] = (
    "Do the documents show that the same damage was claimed twice, or that "
    "an invoice was altered after it was issued?")


STORM_EVIDENCE = [
    {"evidence_id": "E1", "kind": "incident_report", "name": STORM_REPORT},
    {"evidence_id": "E2", "kind": "invoice", "name": STORM_INVOICE},
]
GRADUAL_EVIDENCE = [
    {"evidence_id": "E1", "kind": "incident_report", "name": STORM_REPORT},
    {"evidence_id": "E2", "kind": "invoice", "name": STORM_INVOICE},
    {"evidence_id": "E3", "kind": "assessor_report", "name": GRADUAL_REPORT},
]
THEFT_EVIDENCE = [
    {"evidence_id": "E1", "kind": "incident_report", "name": NO_ENTRY_REPORT},
]
CROP_EVIDENCE = [
    {"evidence_id": "E1", "kind": "holding_statement",
     "name": HOLDING_STATEMENT},
    {"evidence_id": "E2", "kind": "weather_record", "name": RAINFALL_RECORD},
]
DIRECTED_EVIDENCE = [
    {"evidence_id": "E1", "kind": "incident_report", "name": DIRECTED_REPORT},
    {"evidence_id": "E2", "kind": "invoice", "name": STORM_INVOICE},
]

STORM_INCIDENT = {
    "incident_summary": "A storm on the night of 2 to 3 March 2026 lifted "
                        "the roof covering and water entered the stockroom, "
                        "damaging racking, stock and ceiling panels.",
    "incident_date": "2026-03-03",
    "incident_location_reference": "SYN-UNIT-4",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}

THEFT_INCIDENT = {
    "incident_summary": "Stock and a laptop were found missing from the "
                        "unit on the morning of 29 July 2026.",
    "incident_date": "2026-07-29",
    "incident_location_reference": "SYN-UNIT-12",
    "claimed_loss_category": "contents",
    "claimed_amount_band": "1000-5000",
}

CROP_INCIDENT = {
    "incident_summary": "The 2026 growing window closed with recorded "
                        "rainfall below the level the schedule insures "
                        "against at the named station.",
    "incident_date": "2026-09-30",
    "incident_location_reference": "SYN-PLOT-7",
    "claimed_loss_category": "parametric drought",
    "claimed_amount_band": "fixed payout",
}


class Harness:
    """One deployed contract plus the mocking a round needs."""

    def __init__(self, vm, contract, accounts):
        self.vm = vm
        self.contract = contract
        self.insurer = accounts[0]
        self.claimant = accounts[1]
        self.stranger = accounts[2]
        self.vm.warp(TODAY)

    # -- mocking ------------------------------------------------------------

    def mock_doc(self, name, status=200, body=None, url=None):
        self.vm.mock_web(
            url_pattern=self._pattern(url or url_for(name)),
            response={"method": "GET", "status": status,
                      "body": doc_text(name) if body is None else body},
        )

    def mock_docs(self, *names):
        for name in names:
            self.mock_doc(name)

    def mock_panel(self, raw):
        self.vm.mock_llm(prompt_pattern="assess one insurance claim",
                         response=raw)

    def panel(self, conditions, exclusions=None, sufficient=True,
              contradiction=False, contradiction_quote="",
              contradiction_id="", trigger=None, fraud=None):
        """Build a panel answer. `conditions` and `exclusions` are lists of
        (ref, finding, quote, evidence_id)."""
        answer = {
            "conditions": [
                {"ref": row[0], "finding": row[1], "quote": row[2],
                 "evidence_id": row[3], "basis": "synthetic test row"}
                for row in conditions],
            "exclusions": [
                {"ref": row[0], "finding": row[1], "quote": row[2],
                 "evidence_id": row[3], "basis": "synthetic test row"}
                for row in (exclusions or [])],
            "evidence": {"sufficient": sufficient,
                         "contradiction": contradiction,
                         "quote": contradiction_quote,
                         "evidence_id": contradiction_id,
                         "basis": "synthetic test row"},
            "trigger": trigger or {"value_found": False, "value": 0,
                                   "quote": "", "evidence_id": ""},
            "fraud": fraud or {"finding": "NOT_ASKED", "quote": "",
                               "evidence_id": "", "basis": ""},
        }
        return json.dumps(answer)

    @staticmethod
    def _pattern(url):
        return url.replace(".", r"\.") + "$"

    # -- contract convenience ----------------------------------------------

    def register(self, definition=None, policy=POLICY_PROPERTY,
                 coverage_type="small commercial property"):
        self.vm.sender = self.insurer
        return self.contract.register_policy(
            url_for(policy), doc_sha(policy), coverage_type,
            json.dumps(definition or PROPERTY_DEFINITION))

    def open_challenge(self, policy_id, required=None, deadline=DEADLINE,
                       question=None, sender=None):
        self.vm.sender = sender or self.insurer
        return self.contract.open_claim_challenge(
            policy_id,
            question or "Does this claim satisfy the conditions of cover for "
                        "the damage claimed, and does any exclusion apply?",
            json.dumps(required if required is not None
                       else ["incident_report", "invoice"]),
            deadline)

    def submit(self, claim_id, evidence=None, incident=None,
               reference="SYN-2041", sender=None):
        self.vm.sender = sender or self.claimant
        documents = []
        for item in (evidence if evidence is not None else STORM_EVIDENCE):
            documents.append({
                "evidence_id": item["evidence_id"], "kind": item["kind"],
                "url": item.get("url", url_for(item.get("name", ""))),
                "sha256": item.get("sha256",
                                   doc_sha(item["name"])
                                   if "name" in item else "0" * 64),
            })
        return self.contract.submit_claim(
            claim_id, reference,
            json.dumps(incident if incident is not None else STORM_INCIDENT),
            json.dumps(documents))

    def resolve(self, submission_id, sender=None):
        self.vm.sender = sender or self.stranger
        return self.contract.resolve_submission(submission_id)

    def set_clock(self, timestamp):
        """Move the transaction clock the contract reads.

        On a real network every transaction carries its own datetime. Direct
        Mode injects one when the contract is loaded and `vm.warp` after that
        does not reach it, so a test that needs a later transaction moves the
        injected value as well. Nothing in the contract is patched.
        """
        self.vm.warp(timestamp)
        module = sys.modules[type(self.contract).__module__]
        module.gl.message_raw["datetime"] = timestamp

    def clear(self):
        self.vm.clear_mocks()


@pytest.fixture
def harness():
    vm = VMContext()
    vm.check_pickling = True
    with vm.activate():
        accounts = create_test_addresses(4)
        vm.sender = accounts[0]
        vm.warp(TODAY)
        contract = deploy_contract(CONTRACT, vm)
        yield Harness(vm, contract, accounts)


@pytest.fixture
def ready(harness):
    """A property policy registered, a challenge open, and every document
    reachable: the state most adjudication tests start from."""
    policy_id = harness.register()
    claim_id = harness.open_challenge(policy_id)
    harness.mock_docs(POLICY_PROPERTY, STORM_REPORT, STORM_INVOICE)
    return harness, policy_id, claim_id
