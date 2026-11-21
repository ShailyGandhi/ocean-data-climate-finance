"""Figure 1: five-layer conceptual framework (Table 1).

Run:  python make_figure1.py   ->  figure1_framework.png / .pdf in this folder
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

OUT = Path(__file__).resolve().parent
LAYERS = [
    ("Ocean Observations", ["GOOS", "Argo", "WOD"]),
    ("Data Integration", ["Standardization", "Harmonization"]),
    ("Indicators", ["Hazard proxy", "Ecosystem stress", "Low-elevation population exposure"]),
    ("Decision Support", ["Planning", "Prioritization"]),
    ("Finance Mechanisms", ["Blue Bonds", "Climate Funds", "Investment"]),
]
W, ROW, GAP = 100.0, 4.5, 4.5  # width, height of each row, gap holding the arrow


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13})
    total = len(LAYERS) * 2 * ROW + (len(LAYERS) - 1) * GAP
    fig, ax = plt.subplots(figsize=(10.7, 6.35))
    ax.set_xlim(-0.5, W + 0.5)
    ax.set_ylim(-0.5, total + 0.5)
    ax.axis("off")
    y = total
    for k, (name, parts) in enumerate(LAYERS):
        y -= ROW
        ax.add_patch(Rectangle((0, y), W, ROW, fill=False, lw=1.6))
        ax.text(W / 2, y + ROW / 2, name, ha="center", va="center")
        y -= ROW
        w = W / len(parts)
        for i, part in enumerate(parts):
            ax.add_patch(Rectangle((i * w, y), w, ROW, fill=False, lw=1.6))
            ax.text(i * w + w / 2, y + ROW / 2, part, ha="center", va="center",
                    fontsize=13 if len(part) < 25 else 10.3)
        if k < len(LAYERS) - 1:
            top, bot, cx = y, y - GAP, W / 2
            shaft, head = 1.6, 3.2
            ax.add_patch(Polygon([(cx - shaft, top), (cx + shaft, top), (cx + shaft, bot + 2.4),
                                  (cx + head, bot + 2.4), (cx, bot), (cx - head, bot + 2.4),
                                  (cx - shaft, bot + 2.4)], closed=True, fill=False, lw=1.4))
            y = bot
    fig.savefig(OUT / "figure1_framework.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(OUT / "figure1_framework.pdf", bbox_inches="tight", pad_inches=0.03)


if __name__ == "__main__":
    main()
