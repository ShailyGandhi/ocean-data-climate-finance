"""Figure 4 (revised, Round 2): ocean data value chain behind the five-layer framework.

Run:  python make_figure4.py   ->  figure4_value_chain.png / .pdf in this folder
Requires: matplotlib
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent

STAGES = [
    dict(name="1. Ocean\nObservations",
         role="Sustained observations\nof Essential Ocean\nVariables",
         study="Satellite altimetry\n(NOAA LSA)\nTide gauges, 18 SIDS\n(PSMSL)\nHeat content\n0–2000 m (NCEI)\npH, Ωar (HOT,\nStation ALOHA)",
         out="Quality-controlled\ntime series\nwith metadata",
         implemented=True),
    dict(name="2. Data\nIntegration",
         role="Harmonize period,\nbaseline, units; link\nexposure and finance",
         study="Period 1993–2024\nBaseline 1995–2014\nGauge → country\nPopulation, land\nbelow 5 m\n(World Bank)\nOECD finance,\n2024 prices",
         out="Decision-scale\ndataset traceable\nto its sources",
         implemented=True),
    dict(name="3. Indicators",
         role="Hazard, ecosystem-\nstress and exposure\nindicators",
         study="H: relative sea-level\ntrend\npH and Ωar trends\nE: % population\nbelow 5 m\nF: finance per\nexposed resident",
         out="Indicators with\nstated uncertainty",
         implemented=True),
    dict(name="4. Decision\nSupport",
         role="Explicit, reproducible\nscreening rules",
         study="H, E and F flags\nfor 18 SIDS\n\nSensitivity tests:\nsignificance-based H;\nalternative E and F;\nalternative gauge\n(Maldives)",
         out="Screening\ninformation\n(not a ranking)",
         implemented=True),
    dict(name="5. Finance\nMechanisms",
         role="Project identification,\nrisk assessment,\ninstruments, MRV",
         study="Current adaptation-\nrelated finance flows\n(OECD, 2014–2024)\n\nBlue-bond indicators\nproposed, not\nimplemented",
         out="Investment-relevant\ninformation\n(future work)",
         implemented=False),
]

HEAD = "#1f4e79"
BODY = "#eef3f8"
GREY = "#8a8a8a"


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    n = len(STAGES)
    gap = 3.2
    w = (100 - gap * (n - 1)) / n
    top, head_h, role_h, study_h, out_h = 97, 9, 12, 41, 12

    for i, s in enumerate(STAGES):
        x = i * (w + gap)
        ls = "-" if s["implemented"] else (0, (4, 2))
        y_head = top - head_h
        ax.add_patch(FancyBboxPatch((x, y_head), w, head_h, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=HEAD if s["implemented"] else "white", ec=HEAD, lw=1.0, ls=ls))
        ax.text(x + w / 2, y_head + head_h / 2, s["name"], ha="center", va="center", fontsize=8,
                fontweight="bold", color="white" if s["implemented"] else HEAD)

        y_role = y_head - role_h
        ax.text(x + w / 2, y_role + role_h / 2, s["role"], ha="center", va="center", fontsize=6.2,
                style="italic", color="#333333")

        y_study = y_role - study_h
        ax.add_patch(FancyBboxPatch((x, y_study), w, study_h, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=BODY if s["implemented"] else "white", ec=HEAD, lw=0.8, ls=ls))
        #ax.text(x + w / 2, y_study + study_h - 2.2, "In this study", ha="center", va="top", fontsize=6.8,
        #        fontweight="bold", color=HEAD)
        ax.text(x + w / 2, y_study + study_h - 7.0, s["study"], ha="center", va="top", fontsize=6.3,
                linespacing=1.25)

        y_out = y_study - 4 - out_h
        ax.add_patch(FancyBboxPatch((x, y_out), w, out_h, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="white", ec=HEAD, lw=0.8, ls=ls))
        ax.text(x + w / 2, y_out + out_h / 2, s["out"], ha="center", va="center", fontsize=6.6)
        ax.add_patch(FancyArrowPatch((x + w / 2, y_study), (x + w / 2, y_out + out_h),
                                     arrowstyle="-|>", mutation_scale=7, color=GREY, lw=0.8))

        if i < n - 1:
            ya = y_study + study_h / 2
            ax.add_patch(FancyArrowPatch((x + w + 0.3, ya), (x + w + gap - 0.3, ya),
                                         arrowstyle="-|>", mutation_scale=9, color=HEAD, lw=1.2))

    y_band = 8.5
    ax.add_patch(FancyBboxPatch((0, y_band), 100, 7, boxstyle="round,pad=0,rounding_size=1.2",
                                fc="#f6f1e4", ec="#b08d3c", lw=0.8))
    ax.text(50, y_band + 3.5,
            "Provenance (source, retrieval date, checksum) and uncertainty are carried through all five stages",
            ha="center", va="center", fontsize=7, color="#5a4615")

    ax.plot([1, 5], [2.2, 2.2], color=HEAD, lw=1.2)
    ax.text(6, 2.2, "implemented with open data in this study", va="center", fontsize=6.6)
    ax.plot([52, 56], [2.2, 2.2], color=HEAD, lw=1.2, ls=(0, (4, 2)))
    ax.text(57, 2.2, "characterized or proposed only", va="center", fontsize=6.6)

    fig.savefig(OUT / "figure4_value_chain.png", dpi=400, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT / "figure4_value_chain.pdf", bbox_inches="tight", pad_inches=0.05)


if __name__ == "__main__":
    main()
