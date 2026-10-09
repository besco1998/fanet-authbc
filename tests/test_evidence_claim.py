"""What a receiver keeps as evidence, and what the documents say it keeps (audits F80, F81).

The paper, the thesis and docs/01 said that two signed records for one sequence number are
"transferable evidence because both carry the sender's signature". One signature covers a
frame, and until 2026-10-09 the receiver kept records and discarded frames: nothing it held
could be checked by anyone else. A test had passed throughout; it counted the pairs.

Held here: that the receiver keeps the frames, that what it keeps is checked with the sender's
public key and no state of the receiver, and that the documents say this and no more. The
behaviour itself is tested in tests/unit/placement/test_session_v2.py.
"""
from __future__ import annotations

import dataclasses
import inspect
import re
from pathlib import Path

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import session_v2, wire_v2
from authbc.placement.session_v2 import (
    LeanReceiver,
    LeanSender,
    Receipt,
    proves_equivocation,
    verified_records,
)

REPO = Path(__file__).resolve().parents[1]
_SK, _PK = Ed25519Scheme().keygen(seed=bytes(range(32)))
B = 4


def _records(seed: int) -> list[Record]:
    chain = Chain(src=7)
    for i, r in enumerate(telemgen.samples(seed=seed, n=B)):
        chain.append({k: getattr(r, k) for k in wire_v2.PAYLOAD_FIELDS}, ts=1_000 + 20 * i)
    return chain.records()


def _text(relative: str) -> str:
    return re.sub(r"\s+", " ", (REPO / relative).read_text(encoding="utf-8"))


class TestWhatTheReceiverKeeps:
    def _equivocated(self) -> LeanReceiver:
        rx = LeanReceiver({7: _PK})
        assert rx.receive(LeanSender(_SK).frame(_records(3))).receipt is Receipt.ACCEPTED
        assert rx.receive(LeanSender(_SK).frame(_records(99))).receipt is Receipt.EQUIVOCATION
        return rx

    def test_a_record_still_holds_no_signature_which_is_why_the_frame_is_kept(self) -> None:
        assert {f.name for f in dataclasses.fields(Record)} == {"src", "seq", "ts", "prev_hash",
                                                                "pl"}
        (first, second), = self._equivocated().store.equivocations
        assert isinstance(first, Record) and isinstance(second, Record)

    def test_the_receiver_keeps_frames_and_the_two_of_an_equivocation(self) -> None:
        rx = self._equivocated()
        assert set(vars(rx)) == {"_pks", "_last", "_frames", "evidence", "store", "counters"}
        (kept,) = rx.evidence
        assert isinstance(kept.held, bytes) and isinstance(kept.offered, bytes)
        assert rx.frame_of(kept.src, kept.seq) == kept.held

    def test_a_third_party_needs_the_public_key_and_nothing_of_the_receiver(self) -> None:
        """The two checks are functions of the frames and the key: no receiver is passed."""
        for check in (verified_records, proves_equivocation):
            assert "self" not in inspect.signature(check).parameters
            assert inspect.getmodule(check) is session_v2
        assert list(inspect.signature(proves_equivocation).parameters) == ["held", "offered",
                                                                           "pk"]
        (kept,) = self._equivocated().evidence
        del self                                    # nothing of the receiver is in reach below
        assert proves_equivocation(kept.held, kept.offered, _PK)
        shown = verified_records(kept.held, _PK)
        assert shown is not None and [r.seq for r in shown] == [0, 1, 2, 3]


class TestTheDocumentsSayThisAndNoMore:
    PAPER = _text("paper/main.tex")
    THREAT = _text("thesis/ch03_system_model.tex")
    CONCLUSIONS = _text("thesis/ch12_conclusions.tex")
    MODEL = _text("docs/01_SYSTEM_MODEL_ARCHITECTURE.md")

    def test_the_withdrawn_sentence_is_gone(self) -> None:
        for text in (self.PAPER, self.THREAT, self.MODEL):
            assert "so the pair is transferable proof" not in text
            assert "transferable evidence because both carry" not in text

    def test_no_document_still_says_the_store_lacks_the_frames(self) -> None:
        for text in (self.PAPER, self.CONCLUSIONS, self.MODEL):
            assert "not yet evidence to anyone else" not in text
            assert "not the frames or signatures" not in text

    def test_the_paper_says_a_record_is_evidence_only_with_its_frame(self) -> None:
        assert "a record is evidence only with its frame" in self.PAPER
        assert "a third party checks the pair with the sender's public key alone" in self.PAPER
        assert "The receiver therefore keeps every accepted frame, at its on-air length for " \
               "every $b$ records held" in self.PAPER

    def test_the_thesis_keeps_the_history_visible(self) -> None:
        """What was wrong stays in the text beside what is done now."""
        for needle in ("Until 2026-10-09 the receiver of this prototype kept verified records "
                       "and discarded the frame",
                       "it counted the pairs and never asked whether one could be checked",
                       "The receiver now keeps every accepted frame as it arrived",
                       "Fixing this found a second defect",
                       "refused as a replay"):
            assert needle in self.THREAT, needle

    def test_the_system_model_names_where_each_check_lives(self) -> None:
        for needle in ("`LeanReceiver.evidence`", "`session_v2.proves_equivocation`",
                       "`LeanReceiver.frame_of`", "`session_v2.verified_records`"):
            assert needle in self.MODEL, needle
