"""The kit for the hardware sessions of 2026-11-21 (predictions/W1p.md, W1q.md, W1r.md), tested off
the boards: `hw/channel/rssi.sh`, `bcast_rx.py --timestamps` and `run_window_plan2.sh`.

Plans: docs/revision/2026-11-20_session_plans.md, approved by Mohamed 2026-11-21.
"""
from __future__ import annotations

import csv
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

CHANNEL = Path(__file__).resolve().parents[1] / "hw" / "channel"


class TestTheRssiQuery:
    """rssi.sh asks the firmware's GET_RSSI (127) with a peer's address, through the vendor
    command frameburst.sh uses, and reads val from the reply's data attribute."""

    @staticmethod
    def _run(tmp_path: Path, reply: str, arg: str) -> tuple[int, str, str]:
        fake = tmp_path / "iw"
        args = tmp_path / "args"
        fake.write_text(f"#!/bin/bash\necho \"$@\" > {args}\necho 'vendor response: {reply}'\n")
        fake.chmod(0o755)
        run = subprocess.run(["bash", str(CHANNEL / "rssi.sh"), arg],
                             env={"IW": str(fake), "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=False)
        sent = args.read_text().strip() if args.exists() else ""
        return run.returncode, run.stdout.strip(), sent

    # data attribute (type 2, length 16): val = −45 (d3 ff ff ff), then the echoed address and pad;
    # then the length attribute (type 1) = 12
    REPLY = "10 00 02 00 d3 ff ff ff 11 22 33 44 55 66 00 00 06 00 01 00 0c 00 00 00"

    def test_a_negative_value_is_read_signed(self, tmp_path: Path) -> None:
        code, out, _ = self._run(tmp_path, self.REPLY, "11:22:33:44:55:66")
        assert (code, out) == (0, "-45")

    def test_the_order_of_the_attributes_does_not_matter(self, tmp_path: Path) -> None:
        reply = "06 00 01 00 0c 00 00 00 10 00 02 00 a6 ff ff ff 00 00 00 00 00 00 00 00"
        assert self._run(tmp_path, reply, "any")[:2] == (0, "-90")

    def test_the_command_carries_cmd_127_length_12_and_the_address(self, tmp_path: Path) -> None:
        _, _, sent = self._run(tmp_path, self.REPLY, "aa:bb:cc:0d:0e:0f")
        words = sent.split()
        assert words[:6] == ["dev", "wlan0", "vendor", "recv", "0x001018", "0x1"]
        payload = [int(w, 16) for w in words[6:]]
        assert payload[:20] == [0x7f, 0, 0, 0, 12, 0, 0, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        assert payload[20:24] == [0, 0, 0, 0]                       # val
        assert payload[24:30] == [0xaa, 0xbb, 0xcc, 0x0d, 0x0e, 0x0f]  # ea
        assert len(payload) == 20 + 12                               # the struct with its padding

    def test_any_sends_the_zero_address(self, tmp_path: Path) -> None:
        _, _, sent = self._run(tmp_path, self.REPLY, "any")
        assert [int(w, 16) for w in sent.split()[6:]][24:30] == [0] * 6

    def test_a_reply_without_data_is_an_error_and_not_a_number(self, tmp_path: Path) -> None:
        code, out, _ = self._run(tmp_path, "06 00 01 00 0c 00 00 00", "any")
        assert code != 0 and out.startswith("error")

    @pytest.mark.parametrize("bad", ["", "11:22:33:44:55", "zz:22:33:44:55:66", "1122334455"])
    def test_a_malformed_address_is_refused(self, tmp_path: Path, bad: str) -> None:
        assert self._run(tmp_path, self.REPLY, bad)[0] == 2


class TestTheReceiveTimestamps:
    @staticmethod
    def _receive(tmp_path: Path, timestamps: bool, seqs: list[int]) -> tuple[dict, Path]:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        out = tmp_path / "rx.json"
        ts = tmp_path / "ts.csv"
        cmd = [sys.executable, str(CHANNEL / "bcast_rx.py"), "--port", str(port),
               "--seconds", "2.5", "--out", str(out)]
        if timestamps:
            cmd += ["--timestamps", str(ts)]
        rx = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
        time.sleep(0.8)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tx:
            for s in seqs:
                tx.sendto(f"{s:<10}".encode() + b"x" * 30, ("127.0.0.1", port))
                time.sleep(0.01)
        rx.wait(timeout=10)
        return json.loads(out.read_text()), ts

    def test_every_frame_gets_a_kernel_time_in_order(self, tmp_path: Path) -> None:
        got, ts = self._receive(tmp_path, True, list(range(20)))
        assert got["received_unique"] == 20
        rows = list(csv.DictReader(ts.open()))
        assert [int(r["seq"]) for r in rows] == list(range(20))
        t = [int(r["t_ns"]) for r in rows]
        assert all(x > 0 for x in t)
        gaps = [b - a for a, b in zip(t, t[1:], strict=False)]
        assert all(g > 0 for g in gaps)
        # sent 10 ms apart: the kernel times must say so, within the sender's own sleep jitter
        assert 0.005e9 < sorted(gaps)[len(gaps) // 2] < 0.05e9

    def test_without_the_option_no_file_and_the_same_record(self, tmp_path: Path) -> None:
        got, ts = self._receive(tmp_path, False, [3, 4, 5])
        assert not ts.exists()
        assert set(got) == {"received_unique", "duplicates", "min_seq", "max_seq", "span_s",
                            "rcvbuf_bytes", "self", "by_source"}
        assert got["received_unique"] == 3


class TestTheSessionRunner:
    @staticmethod
    def _dry(tmp_path: Path, node: int, lines: list[str], start: int = 1_000) -> list[str]:
        plan = tmp_path / "plan.txt"
        plan.write_text("# nodes: 1,2,3\n" + "\n".join(lines) + "\n")
        run = subprocess.run(["bash", str(CHANNEL / "run_window_plan2.sh"), str(node), str(start),
                              str(plan)], env={"DRY": "1", "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=False)
        assert run.returncode == 0, run.stderr
        return run.stdout.strip().splitlines()

    def test_windows_open_one_after_another_by_their_own_lengths(self, tmp_path: Path) -> None:
        out = self._dry(tmp_path, 1, ["A 50 145 1", "B 600 145 1,2 40", "C 131 145 2,3 90"])
        opens = [int(ln.split()[4]) for ln in out[:3]]
        secs = [int(ln.split()[6]) for ln in out[:3]]
        assert secs == [25, 40, 90]                      # the default is 25 s
        assert opens == [1_000, 1_000 + 25 + 5, 1_000 + 25 + 5 + 40 + 5]
        assert out[3] == f"session_s {25 + 40 + 90 + 3 * 5 + 120}"

    def test_each_node_takes_only_its_own_power(self, tmp_path: Path) -> None:
        lines = ["P0 600 145 1,2 25 1:1500,2:auto", "P3 600 145 1,2 25 1:1200"]
        assert [ln.split()[-1] for ln in self._dry(tmp_path, 1, lines)[:2]] == ["1500", "1200"]
        n2 = self._dry(tmp_path, 2, lines)[:2]
        assert n2[0].endswith("power auto") and n2[1].endswith("power -")

    def test_a_window_shorter_than_ten_seconds_is_refused(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.txt"
        plan.write_text("# nodes: 1,2\nA 50 145 1 5\n")
        run = subprocess.run(["bash", str(CHANNEL / "run_window_plan2.sh"), "1", "0", str(plan)],
                             env={"DRY": "1", "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=False)
        assert run.returncode == 2

    def test_frame_burst_is_set_off_after_joining_and_logged_around_the_windows(self) -> None:
        text = (CHANNEL / "run_window_plan2.sh").read_text()
        joined = text.index("ibss join")
        asked = text.index('frameburst.sh" set 0')
        before = text.index("frameburst before the windows")
        windows = text.index('for k in "${!WINDOWS[@]}"; do\n    read -r label')
        after = text.index("frameburst after the windows")
        assert joined < asked < before < windows < after

    def test_every_window_keeps_timestamps_and_two_signal_readings(self) -> None:
        text = (CHANNEL / "run_window_plan2.sh").read_text()
        assert '--timestamps "$OUT/rxts_node${NODE}_$tag.csv"' in text
        assert 'rssi_line "$tag" mid' in text and 'rssi_line "$tag" after' in text
        assert 'rssi.sh" any' in text

    def test_the_way_out_restores_automatic_power_and_frame_burst(self) -> None:
        text = (CHANNEL / "run_window_plan2.sh").read_text()
        restore = text[text.index("restore() {"):text.index("rssi_line() {")]
        assert "set txpower auto" in restore and "revert_adhoc.sh" in restore
        assert 'frameburst.sh" set 1' in (CHANNEL / "revert_adhoc.sh").read_text()
