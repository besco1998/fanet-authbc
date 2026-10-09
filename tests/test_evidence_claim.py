"""What a receiver keeps as evidence, and what the documents say it keeps (audit F80).

The paper, the thesis and docs/01 said that two signed records for one sequence number are
"transferable evidence because both carry the sender's signature". The signature covers a
frame, and the store keeps records: the pair it retains cannot be checked by anyone else.
Held here: the fact as the code has it, and that no document claims more. When the store is
made to keep frames (docs/OPEN_ITEMS.md G28), the first class changes and the second is
rewritten with it.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.record import Record
from authbc.placement import wire_v2
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt

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

    def test_the_retained_pair_is_two_records_and_a_record_holds_no_signature(self) -> None:
        (first, second), = self._equivocated().store.equivocations
        assert isinstance(first, Record) and isinstance(second, Record)
        assert (first.src, first.seq) == (second.src, second.seq) and first != second
        assert {f.name for f in dataclasses.fields(Record)} == {"src", "seq", "ts", "prev_hash",
                                                                "pl"}

    def test_neither_the_receiver_nor_its_store_keeps_a_frame(self) -> None:
        """One signature covers a frame, so a record is checkable only with its frame. The
        names below are everything the two objects hold."""
        rx = self._equivocated()
        assert set(vars(rx)) == {"_pks", "_last", "store", "counters"}
        assert set(vars(rx.store)) == {"_accepted", "_last_seq", "_records", "equivocations",
                                       "counters"}


class TestNoDocumentClaimsMore:
    PAPER = _text("paper/main.tex")
    THREAT = _text("thesis/ch03_system_model.tex")
    MODEL = _text("docs/01_SYSTEM_MODEL_ARCHITECTURE.md")

    def test_the_withdrawn_sentence_is_gone(self) -> None:
        for text in (self.PAPER, self.THREAT, self.MODEL):
            assert "so the pair is transferable proof" not in text
            assert "transferable evidence because both carry" not in text

    def test_the_paper_says_what_evidence_needs_and_that_the_store_lacks_it(self) -> None:
        assert "Each is evidence to a third party only together with the frame that carried it" \
            in self.PAPER
        assert "The prototype's store keeps verified records and not the frames and signatures " \
               "that carried them" in self.PAPER

    def test_the_thesis_and_the_system_model_say_the_same(self) -> None:
        assert "the store of this prototype does not keep it" in self.THREAT
        assert "not yet something a third party can check" in self.THREAT
        assert "The store keeps the two records, not the frames or signatures" in self.MODEL
