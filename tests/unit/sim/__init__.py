"""Unit tests for `authbc.sim` — the NS-3 PHY-trace analyser and the independent slot simulator.

These guard the tooling that *checks* the channel models, so they must not depend on those models:
`dcf_ladder` was written before Ma & Chen's paper was found and is retained precisely as an
independent cross-check.
"""
