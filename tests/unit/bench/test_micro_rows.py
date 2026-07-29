"""E5 — the P1 measurement harness's row builders (guards src/authbc/bench/micro.py).

`micro.py` sat at 46 % coverage as "measurement plumbing". The justification failed in practice: on
2026-07-29 two bugs were introduced into `measure_crypto` while adding the SHA-256 chain-link row,
and **both were caught by running on hardware rather than by any test** —

  1. `_time_row` was called without its keyword-only `expensive` argument (a crash, but only on the
     Pi, minutes into a run);
  2. the emitted row reported `msg_bytes=200` when the measured input was 45 B — a *silent*
     provenance error that would have been frozen into an artifact.

The timing primitive itself (`timers.time_op`) is tested separately; what was untested is the layer
that decides WHAT is measured and HOW it is labelled. That is what these tests cover. They use a
tiny fake operation so they stay fast — the point is the row contract, not the timings.
"""

from __future__ import annotations

import pytest

from authbc.bench import micro


def _rows_by_op(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {(r["scheme"], r["op"], str(r["agg_b"])): r for r in rows}


@pytest.fixture(scope="module")
def crypto_rows() -> list[dict]:
    """One real measurement pass. Module-scoped: the crypto is genuine, so it is not free."""
    return micro.measure_crypto(seed=1)


def test_every_row_has_the_full_schema(crypto_rows: list[dict]) -> None:
    expected = {"scheme", "op", "agg_b", "msg_bytes", "median_ns",
                "ci_lo_ns", "ci_hi_ns", "n_ops", "checksum"}
    for r in crypto_rows:
        assert set(r) == expected, f"schema drift in {r.get('scheme')}/{r.get('op')}"


def test_the_chain_hash_row_reports_its_own_input_size(crypto_rows: list[dict]) -> None:
    """Bug 2, pinned. The SHA-256 row hashes a 45 B record, NOT the 200 B crypto message.

    A frozen artifact that misstates its own input is worse than no artifact — it looks
    authoritative and is wrong.
    """
    row = _rows_by_op(crypto_rows)[("sha256", "chain_link", "")]
    assert row["msg_bytes"] == micro.CHAIN_MSG_BYTES == 45
    assert row["msg_bytes"] != micro.MSG_BYTES


def test_signature_rows_report_the_crypto_message_size(crypto_rows: list[dict]) -> None:
    """The default must still apply where it is correct — the fix must not over-generalize."""
    for (scheme, op, _agg), row in _rows_by_op(crypto_rows).items():
        if scheme != "sha256":
            assert row["msg_bytes"] == micro.MSG_BYTES, f"{scheme}/{op}"


def test_expected_operations_are_all_present(crypto_rows: list[dict]) -> None:
    """Bug 1's real consequence: a missing or failed row silently shrinks the measured set."""
    keys = _rows_by_op(crypto_rows)
    for scheme in ("ed25519", "ecdsa_p256", "bls"):
        assert (scheme, "sign", "") in keys
        assert (scheme, "verify", "") in keys
    assert ("sha256", "chain_link", "") in keys
    for b in micro.BATCH_SIZES:
        assert ("bls", "aggregate", str(b)) in keys
        assert ("bls", "agg_verify", str(b)) in keys


def test_timings_are_positive_and_bracketed_by_their_ci(crypto_rows: list[dict]) -> None:
    for r in crypto_rows:
        assert r["median_ns"] > 0, f"{r['scheme']}/{r['op']} non-positive median"
        assert r["ci_lo_ns"] <= r["median_ns"] <= r["ci_hi_ns"], (
            f"{r['scheme']}/{r['op']} median outside its own CI")
        assert r["n_ops"] > 0


def test_the_hash_is_far_cheaper_than_a_signature(crypto_rows: list[dict]) -> None:
    """Sanity gate on the D7 input: if SHA-256 ever measures near signature cost, something is
    wrong with the harness, not with SHA-256."""
    keys = _rows_by_op(crypto_rows)
    h = keys[("sha256", "chain_link", "")]["median_ns"]
    sign = keys[("ed25519", "sign", "")]["median_ns"]
    assert h < sign / 5, f"chain hash {h} ns vs Ed25519 sign {sign} ns — implausible"


def test_measure_sizes_row_shape() -> None:
    """Long-form rows: one per (encoding, metric), with the value bracketed by its CI."""
    rows = micro.measure_sizes(seed=1, n=200)
    assert set(rows[0]) == {"encoding", "seed", "n", "metric", "value", "ci_lo", "ci_hi"}
    assert {r["encoding"] for r in rows} >= {"json", "cbor", "msgpack", "delta"}
    for r in rows:
        assert r["value"] > 0, f"{r['encoding']}/{r['metric']}"
        # only the bootstrapped mean carries a CI; max/phi are point statistics and leave it blank
        if r["ci_lo"] != "":
            assert r["ci_lo"] <= r["value"] <= r["ci_hi"], f"{r['encoding']}/{r['metric']}"
        else:
            assert r["metric"] in {"max_bytes", "phi_pct_g64"}, (
                f"{r['metric']} has no CI — only point statistics may omit one")
