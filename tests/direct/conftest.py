"""Shared harness for the Direct Mode suite.

Only the nondeterministic edges are mocked: the two document fetches and the
panel call. Every test exercises the contract's own admission, grounding,
derivation and storage code - nothing stubs out `resolve_review` itself.
"""

import hashlib
import json
import os
import pathlib

import pytest

from eth_utils import to_checksum_address

from gltest.direct import VMContext, deploy_contract, create_test_addresses


def hexaddr(account) -> str:
    """The checksummed spelling a contract stores for a test account."""
    return to_checksum_address(bytes(account))


ROOT = pathlib.Path(__file__).resolve().parents[2]

# The suite runs against the committed contract unless a mutation sweep
# points it at a patched copy (scripts/mutate.py).
CONTRACT = pathlib.Path(
    os.environ.get("CLAIMCOURT_CONTRACT",
                   str(ROOT / "contracts" / "claimcourt.py")))
FIXTURES = ROOT / "fixtures"

# Any https host works against a mocked fetch; these are the locations the
# live suite uses, so the two suites exercise the same admission rules.
BASE = "https://raw.githubusercontent.com/Hemmy1417/ClaimCourt/main/fixtures/"

POLICY = "policy-household-v1.txt"
NOTICE_UNOCCUPIED = "notice-unoccupied.txt"
NOTICE_LATE = "notice-late-notification.txt"
NOTICE_JEWELLERY = "notice-jewellery-limit.txt"
NOTICE_FLOOD = "notice-flood-clause.txt"
NOTICE_DIRECTED = "notice-unoccupied-directed.txt"

TODAY = "2026-10-17T09:30:00.000+00:00"
TODAY_DATE = "2026-10-17"


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
    """A verbatim span of a fixture, so a test quotes what the document
    really says instead of inventing language the contract would reject."""
    text = " ".join(doc_text(name).split())
    position = text.find(needle)
    assert position >= 0, "fixture does not contain " + needle
    return text[position:position + length]


class Harness:
    """One deployed contract plus the mocking the round needs."""

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

    def mock_panel(self, raw):
        self.vm.mock_llm(prompt_pattern="review whether a refusal notice",
                         response=raw)

    def panel_json(self, rows):
        return json.dumps({"grounds": rows})

    def row(self, index=0, located=True, clause_quote="", stated=True,
            notice_quote="", supported="YES", exceeded=False,
            basis="synthetic test row"):
        return {"index": index, "clause_located": located,
                "clause_quote": clause_quote,
                "ground_stated_in_notice": stated,
                "notice_quote": notice_quote, "supported": supported,
                "scope_exceeded": exceeded, "basis": basis}

    @staticmethod
    def _pattern(url):
        return url.replace(".", r"\.") + "$"

    # -- contract convenience ----------------------------------------------

    def register(self, window=0, policy=POLICY):
        self.vm.sender = self.insurer
        return self.contract.register_clause_set(
            "Household contents, synthetic edition 1", url_for(policy),
            doc_sha(policy), window)

    def open_review(self, clause_set_id, notice=NOTICE_UNOCCUPIED,
                    clause_refs=None, grounds=None, reference="SYN-0041",
                    sender=None, notice_sha=None, notice_url=None):
        self.vm.sender = sender or self.claimant
        return self.contract.open_review(
            clause_set_id,
            notice_url or url_for(notice),
            notice_sha or doc_sha(notice),
            reference,
            ["Clause 4.2"] if clause_refs is None else clause_refs,
            ["the insured address was left unoccupied for more than sixty "
             "consecutive days"] if grounds is None else grounds,
        )

    def resolve(self, review_id, sender=None):
        self.vm.sender = sender or self.stranger
        return self.contract.resolve_review(review_id)

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
    """A clause set registered and both documents reachable: the state every
    verdict test starts from."""
    clause_set_id = harness.register()
    harness.mock_doc(POLICY)
    return harness, clause_set_id
