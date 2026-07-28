"""F5 on the LoRa arm — per-frame chaining is the ADOPTED LoRa wire format (docs/02 §9b).

Decision (Mohamed, 2026-07-28): adopt per-frame chaining **on LoRa only**. These tests pin the
asymmetry so it cannot drift: LoRa moves the 32 B chain hash to one-per-frame, 802.11 keeps it
per-record. Expected values are hand-computed from the frame arithmetic, not read back from the
module (Law 6).

Why the arms differ, in one line each:
  * LoRa   — the regional payload limit binds (T2a), so 32 B saved per record becomes MORE records
             per frame, and the duty cycle converts that directly into sustainable record rate.
  * 802.11 — freshness binds (T2a, dC/ds = 1), so the same 32 B buys ~6 % energy and nothing else,
             which does not pay for losing independent per-record tamper-evidence.
"""

from __future__ import annotations

import hashlib

import yaml

from authbc.bench.experiments import REPO, load_config
from authbc.models import lora

H_F, G_A, CHAIN = 40, 64, 32
S_DELTA = 45.0                      # measured delta record incl. its own 32 B prev_hash (E1)
S_DELTA_PER_FRAME = S_DELTA - CHAIN  # 13.0 B once the hash is charged once per frame


def test_lora_config_adopts_per_frame_and_still_carries_the_counterfactual() -> None:
    cfg = load_config("lora")
    assert cfg["adopted_chain_mode"] == "per_frame"
    assert set(cfg["chain_modes"]) == {"per_record", "per_frame"}, \
        "the 802.11-format counterfactual must stay in the sweep as the evidence for the decision"


def test_80211_arm_is_untouched_and_still_chains_per_record() -> None:
    """The decision is LoRa-only: no 802.11 config may name a chain mode at all."""
    for exp in ("e1", "e2", "e3", "e4", "e5"):
        path = REPO / f"experiments/{exp}/config.yaml"
        if not path.exists():
            continue
        cfg = yaml.safe_load(path.read_text())
        assert "chain_mode" not in cfg and "adopted_chain_mode" not in cfg, \
            f"{exp} must keep the D6-frozen per-record wire format implicitly"


def test_per_frame_lets_dr5_carry_more_than_twice_the_records() -> None:
    """Hand-computed at DR5 (N = 242 B, RP002 Table 13), delta encoding, placement B.

    per_record: usable = 242 − 40 − 64 = 138;  b = ⌊138/45⌋ = 3
    per_frame : usable = 242 − 40 − 64 − 32 = 106;  b = ⌊106/13⌋ = 8
    """
    n = lora.EU868_DATA_RATES[5].max_app_payload
    assert n == 242
    b_record = int((n - H_F - G_A) // S_DELTA)
    b_frame = int((n - H_F - G_A - CHAIN) // S_DELTA_PER_FRAME)
    assert (b_record, b_frame) == (3, 8)
    assert lora.max_batch_for_mtu(S_DELTA, G_A, H_F, dr=5) == 3
    assert lora.max_batch_for_mtu(S_DELTA_PER_FRAME, G_A + CHAIN, H_F, dr=5) == 8


def test_the_rate_gain_is_the_ratio_of_batches_not_of_bytes() -> None:
    """Λ = b/(ToA/duty). Frames grow slightly (239 B → 240 B), so the gain is ≈ b-ratio, not 8/3.

    This is the number the decision was made on: ~2.7x the records a node can legally send.
    """
    lam_record = lora.sustainable_record_rate(3, H_F + G_A + 3 * int(S_DELTA), dr=5)
    lam_frame = lora.sustainable_record_rate(
        8, H_F + G_A + CHAIN + 8 * int(S_DELTA_PER_FRAME), dr=5)
    assert 2.6 < lam_frame / lam_record < 2.8
    assert 0.070 < lam_record < 0.080
    assert 0.195 < lam_frame < 0.210


def test_per_frame_chaining_lowers_bytes_per_record_to_thirty() -> None:
    """(40 + 64 + 32 + 8·13)/8 = 240/8 = 30.0 B/record, vs (40+64+3·45)/3 = 239/3 = 79.67."""
    assert (H_F + G_A + CHAIN + 8 * S_DELTA_PER_FRAME) / 8 == 30.0
    assert abs((H_F + G_A + 3 * S_DELTA) / 3 - 79.667) < 0.001


def test_stored_ledger_is_unchanged_so_this_is_a_framing_choice_only() -> None:
    """Both modes reconstruct the same records; only the wire differs.

    prev_hash_{i+1} = H(record_i), so a receiver holding the frame's first link and the records in
    order derives every omitted hash. Nothing is dropped from the ledger — which is why this is a
    LoRa-side framing decision and not a change to the chain itself (docs/01 §4).
    """
    records = [b"rec-%d" % i for i in range(8)]
    genesis = b"\x00" * 32

    # SENDER, per_record (the 802.11 wire format): every link is computed and TRANSMITTED.
    sent_links, cur = [], genesis
    for r in records:
        sent_links.append(cur)
        cur = hashlib.sha256(cur + r).digest()

    # SENDER, per_frame (the adopted LoRa format): only links[0] goes on air.
    on_air = sent_links[0]
    assert on_air == genesis

    # RECEIVER, per_frame: rebuild the omitted links from the records it already has.
    rebuilt, cur = [], on_air
    for r in records:
        rebuilt.append(cur)
        cur = hashlib.sha256(cur + r).digest()

    assert rebuilt == sent_links, "per_frame must reconstruct the per_record chain exactly"
    assert len(sent_links) == 8
    # the saving is exactly the links NOT sent: 7 of 8, at 32 B each
    assert (len(sent_links) - 1) * CHAIN == 224
    # and it is a real reconstruction, not a constant: perturbing one record breaks every later link
    tampered = list(records)
    tampered[3] = b"forged"
    broken, cur = [], on_air
    for r in tampered:
        broken.append(cur)
        cur = hashlib.sha256(cur + r).digest()
    assert broken[:4] == sent_links[:4] and broken[4:] != sent_links[4:]
