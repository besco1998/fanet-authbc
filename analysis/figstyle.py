"""One look for every figure the paper prints (review 2026-10-27, items L-31 and L-34).

The paper is set in the Springer Nature single-column template, whose text and tables are
Computer Modern. Every paper figure is therefore drawn at 4.5 in, the width it prints at, so that
its 9 pt text prints at 9 pt, and in Computer Modern: cmr10 for text and the cm math set. The
layout is fitted inside the canvas and the file is saved uncropped (`SAVE`): a tight crop made
the files 4.13 to 4.47 in wide, and set at 4.5 in their text would print up to 9 % large.

cmr10 has no Unicode minus, en dash or multiplication sign. Tick labels are typeset as math
(`axes.formatter.use_mathtext`), which gives a true minus; labels avoid the other two glyphs.

    @figstyle.paper_figure        # around a function that draws and saves one figure
    fig.savefig(path, **figstyle.SAVE)
"""
from __future__ import annotations

import functools
from collections.abc import Callable

import matplotlib

WIDTH = 4.5                     # in: the printed width in the paper
FONT = 9.0                      # axis labels and titles
TICK = 8.5
LEGEND = 8.5
NOTE = 8.0                      # annotations inside the axes

RC = {
    "font.family": "serif",
    "font.serif": ["cmr10"],
    "mathtext.fontset": "cm",
    "axes.formatter.use_mathtext": True,
    "axes.unicode_minus": True,
    "font.size": FONT,
    "axes.labelsize": FONT,
    "axes.titlesize": FONT,
    "xtick.labelsize": TICK,
    "ytick.labelsize": TICK,
    "legend.fontsize": LEGEND,
    "figure.constrained_layout.use": True,
}
SAVE = {"dpi": 200, "metadata": {"Software": None}}     # no version stamp: byte-stable files

def paper_figure[F: Callable[..., None]](draw: F) -> F:
    """Run `draw` inside the paper's style, and leave the global style as it was."""
    @functools.wraps(draw)
    def wrapped(*args, **kwargs):
        with matplotlib.rc_context(RC):
            return draw(*args, **kwargs)
    return wrapped  # type: ignore[return-value]
