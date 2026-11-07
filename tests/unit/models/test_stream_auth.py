"""Per-packet authenticator sizes of the classical stream-signing schemes (docs/02 §6f).

Every expected value is worked by hand from the scheme's own definition, with the primitives this
project uses elsewhere: a 32 B SHA-256 digest and a 64 B Ed25519 signature.
"""

from __future__ import annotations

import pytest

from authbc.models import stream_auth as sa


class TestWongLamTree:
    def test_a_block_of_four_carries_two_sibling_digests(self) -> None:
        # block signature 64 + two siblings on the path to the root 2 x 32 + position 1
        assert sa.wong_lam_tree_bytes(4, hash_bytes=32, sig_bytes=64) == 64 + 64 + 1

    def test_a_block_of_sixteen_carries_four(self) -> None:
        assert sa.wong_lam_tree_bytes(16, hash_bytes=32, sig_bytes=64) == 64 + 4 * 32 + 1

    def test_a_block_that_is_not_a_power_of_two_pays_for_the_deeper_leaves(self) -> None:
        # five leaves need a tree of depth three
        assert sa.wong_lam_tree_bytes(5, hash_bytes=32, sig_bytes=64) == 64 + 3 * 32 + 1

    def test_a_block_of_one_is_a_signature_per_packet(self) -> None:
        assert sa.wong_lam_tree_bytes(1, hash_bytes=32, sig_bytes=64) == 64 + 1

    def test_the_overhead_never_falls_as_the_block_grows(self) -> None:
        sizes = [sa.wong_lam_tree_bytes(n, hash_bytes=32, sig_bytes=64) for n in range(1, 65)]
        assert sizes == sorted(sizes)

    def test_an_empty_block_is_refused(self) -> None:
        with pytest.raises(ValueError, match="block"):
            sa.wong_lam_tree_bytes(0, hash_bytes=32, sig_bytes=64)


class TestEmss:
    def test_two_hashes_per_packet(self) -> None:
        e = sa.emss(hashes_per_packet=2, hash_bytes=32, sig_bytes=64, sig_period=100)
        assert e.data_packet_bytes == 64
        # one signature packet per hundred carries a signature and the hashes of two packets
        assert e.signature_packet_bytes == 64 + 64
        assert e.packets_per_record == pytest.approx(1.01)
        assert e.bytes_per_record == pytest.approx(64 + 128 / 100)

    def test_a_signature_packet_after_every_packet_is_refused_as_not_emss(self) -> None:
        with pytest.raises(ValueError, match="sig_period"):
            sa.emss(hashes_per_packet=2, hash_bytes=32, sig_bytes=64, sig_period=1)


class TestTheOthers:
    def test_gennaro_rohatgi_carries_one_digest(self) -> None:
        assert sa.gennaro_rohatgi_bytes(hash_bytes=32) == 32

    def test_tesla_is_a_mac_a_disclosed_key_and_an_interval_index(self) -> None:
        # the sizes of its authors' prototype: 80-bit MAC, 80-bit key, 4 B index
        assert sa.tesla_bytes(mac_bytes=10, key_bytes=10, index_bytes=4) == 24

    def test_mavlink2_is_link_id_timestamp_and_tag(self) -> None:
        assert sa.MAVLINK2_SIGNATURE_BYTES == 1 + 6 + 6

    @pytest.mark.parametrize("fn, kwargs", [
        (sa.gennaro_rohatgi_bytes, {"hash_bytes": 0}),
        (sa.tesla_bytes, {"mac_bytes": 0, "key_bytes": 10, "index_bytes": 4}),
    ])
    def test_sizes_must_be_positive(self, fn, kwargs) -> None:
        with pytest.raises(ValueError):
            fn(**kwargs)
