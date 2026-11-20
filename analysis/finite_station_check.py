#!/usr/bin/env python3
"""Work package C: the finite-station form against event simulations of the access rule, N = 2–5.

The form is `src/authbc/models/finite_station.py`, derived in
`docs/revision/2026-11-20_finite_station_derivation.md`. It is a proposal, not a registration:
Mohamed decides whether it is registered against ns-3 or hardware.

**The simulations** (nothing shared with the models but the rule):
* **rule A**, the rule the loss expression was derived for. This is the loop of Mohamed's
  `analysis/closed_form_model.simulate`, given an arrival list instead of building one;
* **ns-3's rule**, `authbc.sim.dcf_ns3rule.run` with the same arrival list.

**The sources** of each station:
* `jitter`: one frame per period, drawn anew in each period (the designated source; the
  hardware's sender);
* `phase`: one frame per period at a fixed random phase;
* `poisson`: the reference.

**The PHYs and loads:**
* 802.11b at 1 Mb/s with the 145 B frame of the 2.4 GHz sessions (T_f = 1 640 µs);
* 802.11a at 6 Mb/s with the 1 400 B frame of the 5 GHz sessions (T_f = 1 940 µs);
* airtime occupancy u = N·f·T_f of 0.3, 0.5, 0.7 and 0.85, up to the hardware's (the 5 GHz pair
  ran 0.48–0.82).

    python analysis/finite_station_check.py   -> results/raw/finite_station_check.csv
"""
from __future__ import annotations

import csv
import io
import math
import random
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import finite_station as fs  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402
from authbc.sim import dcf_ns3rule  # noqa: E402

OUT = REPO / "results" / "raw" / "finite_station_check.csv"
PHYS = {"80211b_145B": (phy.DSSS_1M, uc.A80211B, 145),
        "80211a_1400B": (phy.OFDM_20MHZ_6M, uc.A80211A, 1400)}
NODES = (2, 3, 4, 5)
LOADS = (0.3, 0.5, 0.7, 0.85)
SOURCES = ("jitter", "phase", "poisson")
SEEDS = 10
SIM_S = 100.0


def arrivals(n_nodes: int, f: float, source: str, rng: random.Random) -> list[tuple[float, int]]:
    period, out = 1.0 / f, []
    for i in range(n_nodes):
        if source == "poisson":
            t = rng.expovariate(f)
            while t < SIM_S:
                out.append((t, i))
                t += rng.expovariate(f)
            continue
        phase = rng.random()
        for k in range(int(SIM_S * f)):
            out.append(((k + (rng.random() if source == "jitter" else phase)) * period, i))
    return sorted(out)


def rule_a(arr: list[tuple[float, int]], tf: float, acc: uc.Access,
           rng: random.Random) -> float:
    """Mohamed's simulate() loop (rule A), unchanged but for taking the arrival list."""
    times = [t for t, _ in arr]
    na, ia = len(times), 0
    t_idle, backlog, sent, lost = -1.0, [], 0, 0
    slot, difs, delta, w = acc.slot_s, acc.difs_s, acc.delta_s, acc.w
    while ia < na or backlog:
        t0 = t_idle + difs
        tb = t0 + min(backlog) * slot if backlog else math.inf
        ta = times[ia] if ia < na else math.inf
        if ta < tb and ta < t0:
            backlog.append(0)
            ia += 1
            continue
        ts = min(ta, tb)
        n = int(math.floor((ts - t0) / slot + 1e-9)) if ts >= t0 else 0
        lim, tx, rest = ts + delta + 1e-12, 0, []
        for c in backlog:
            if t0 + c * slot <= lim:
                tx += 1
            else:
                rest.append(c - n)
        while ia < na and times[ia] <= ts + delta:
            tx += 1
            ia += 1
        sent += tx
        if tx > 1:
            lost += tx
        end = (ts + delta if tx > 1 else ts) + tf
        while ia < na and times[ia] < end:
            rest.append(rng.randrange(w))
            ia += 1
        backlog, t_idle = rest, end
    return lost / sent


def ns3_rule(arr: list[tuple[float, int]], n_nodes: int, f: float, tf: float,
             acc: uc.Access, seed: int) -> float:
    r = dcf_ns3rule.run(n_nodes, f, tf, slot_s=acc.slot_s, difs_s=acc.difs_s, w=acc.w,
                        delta_s=acc.delta_s, sim_time_s=SIM_S, seed=seed, arrivals=arr)
    return r.lost / r.frames


def rows() -> list[dict[str, object]]:
    out = []
    for name, (ph, acc, size) in PHYS.items():
        tf = uc.airtime_s(ph, size)
        for n_nodes in NODES:
            for u in LOADS:
                f = u / (n_nodes * tf)
                models = {"p_g5": uc.loss((n_nodes - 1) * f, tf, acc),
                          "p_g25": pc.loss_periodic(n_nodes, f, tf, acc),
                          "p_finite": fs.loss(n_nodes, f, tf, acc)}
                for source in SOURCES:
                    for rule in ("A", "ns3"):
                        ps = []
                        for seed in range(1, SEEDS + 1):
                            rng = random.Random(1000 * seed + n_nodes)
                            arr = arrivals(n_nodes, f, source, rng)
                            ps.append(rule_a(arr, tf, acc, rng) if rule == "A"
                                      else ns3_rule(arr, n_nodes, f, tf, acc, seed))
                        out.append({"phy": name, "n_nodes": n_nodes, "occupancy": u,
                                    "frames_per_s": round(f, 3), "source": source, "rule": rule,
                                    "p_sim": st.mean(ps), "p_sim_se": st.stdev(ps) / SEEDS ** 0.5,
                                    **models})
    return out


def markdown(path: Path = OUT) -> str:
    """The comparison, model over simulation, for the designated (jitter) source: generated."""
    data = [r for r in csv.DictReader(ln for ln in path.open() if not ln.startswith("#"))]

    def get(phy_name: str, n: str, u: str, rule: str) -> dict[str, str]:
        return next(r for r in data if (r["phy"], r["n_nodes"], r["occupancy"], r["source"],
                                        r["rule"]) == (phy_name, n, u, "jitter", rule))
    lines = ["| PHY | N | u | rule A: sim | (G5) | (G25) | **finite** | ns-3 rule: sim | (G5) | "
             "(G25) | **finite** |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in PHYS:
        for n in map(str, NODES):
            for u in map(str, LOADS):
                cells = [name, n, u]
                for rule in ("A", "ns3"):
                    r = get(name, n, u, rule)
                    sim = float(r["p_sim"])
                    cells.append(f"{sim:.5f}")
                    for k in ("p_g5", "p_g25", "p_finite"):
                        ratio = f"{float(r[k]) / sim:.2f}" if sim > 0 else "—"
                        cells.append(f"**{ratio}**" if k == "p_finite" else ratio)
                lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    if "--markdown" in sys.argv:
        print(markdown())
        return
    data = rows()
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "finite_station_check",
                 "config_hash": provenance.config_hash({"phys": str(PHYS), "nodes": NODES,
                                                        "loads": LOADS, "seeds": SEEDS,
                                                        "sim_s": SIM_S})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(data[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(data)
    OUT.write_text(buf.getvalue())
    print(f"wrote {OUT.relative_to(REPO)} ({len(data)} rows)")


if __name__ == "__main__":
    main()
