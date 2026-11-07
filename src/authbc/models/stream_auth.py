"""What a packet carries under the classical stream-signing schemes (docs/02 §6f).

An external review asked where this work stands against schemes that amortise one signature over
many packets. They are not implemented here; each is placed by the two quantities that decide
its cost on a contended channel — authenticator bytes per packet and packets per record — worked
from the scheme's own definition in the paper that introduced it:

    Wong & Lam 1999          block signature + packet position + the sibling digests on the
                             packet's path to the root of a hash tree over the block (their §II-B)
    Gennaro & Rohatgi 1997   each block carries the digest of the next; one signature per stream
    EMSS (Perrig et al. 2000, §3)  each packet carries the digests of several earlier packets;
                             a signature packet at intervals carries a signature and as many digests
    TESLA (Perrig et al. 2000, §2) a MAC, a disclosed key of an earlier interval and an interval
                             index — 10 + 10 + 4 B in its authors' prototype
    MAVLink 2 signing        link id 1 B + timestamp 6 B + truncated SHA-256 tag 6 B

⚠️ Digest and signature sizes are parameters: the papers used MD5, SHA-1 and RSA, and an
80-bit truncation that is no longer collision-resistant. The comparison instantiates each scheme
with the primitives of this project and says so; it is not a figure taken from those papers.
"""

from __future__ import annotations

from dataclasses import dataclass

MAVLINK2_SIGNATURE_BYTES: int = 1 + 6 + 6
_POSITION_BYTES: int = 1       # a packet's index inside its block; blocks here are ≤ 256 packets


def _positive(**sizes: float) -> None:
    for name, value in sizes.items():
        if value <= 0:
            raise ValueError(f"{name} must be > 0, got {value}")


def wong_lam_tree_bytes(block: int, *, hash_bytes: int, sig_bytes: int) -> int:
    """Packet signature under tree chaining with a binary tree over a block of `block` packets."""
    if block < 1:
        raise ValueError(f"a block holds at least one packet, got {block}")
    _positive(hash_bytes=hash_bytes, sig_bytes=sig_bytes)
    depth = (block - 1).bit_length()          # ⌈log2 block⌉: siblings on the deepest leaf's path
    return sig_bytes + depth * hash_bytes + _POSITION_BYTES


def gennaro_rohatgi_bytes(*, hash_bytes: int) -> int:
    """Per-packet cost of the off-line chain: the digest of the next packet."""
    _positive(hash_bytes=hash_bytes)
    return hash_bytes


def tesla_bytes(*, mac_bytes: int, key_bytes: int, index_bytes: int) -> int:
    """Per-packet cost of TESLA with one authentication chain."""
    _positive(mac_bytes=mac_bytes, key_bytes=key_bytes, index_bytes=index_bytes)
    return mac_bytes + key_bytes + index_bytes


@dataclass(frozen=True)
class Emss:
    """EMSS with `hashes_per_packet` digests in every packet and a signature packet per period."""

    data_packet_bytes: int
    signature_packet_bytes: int
    sig_period: int

    @property
    def packets_per_record(self) -> float:
        """Data packets plus their share of the signature packets."""
        return 1.0 + 1.0 / self.sig_period

    @property
    def bytes_per_record(self) -> float:
        """Authentication bytes a record costs, signature packets included."""
        return self.data_packet_bytes + self.signature_packet_bytes / self.sig_period


def emss(*, hashes_per_packet: int, hash_bytes: int, sig_bytes: int, sig_period: int) -> Emss:
    """EMSS sizes; `sig_period` data packets share one signature packet."""
    _positive(hashes_per_packet=hashes_per_packet, hash_bytes=hash_bytes, sig_bytes=sig_bytes)
    if sig_period < 2:
        raise ValueError("sig_period must be ≥ 2: a signature after every packet is not EMSS")
    carried = hashes_per_packet * hash_bytes
    return Emss(carried, sig_bytes + carried, sig_period)
