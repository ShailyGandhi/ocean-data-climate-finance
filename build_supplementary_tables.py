"""Collect every derived table into Supplementary Tables S1 (Figure 2) and S2 (worked example, Table 3, Figure 3)."""
import glob
import os

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "supplementary")
os.makedirs(OUT, exist_ok=True)


def sheet_name(path):
    n = os.path.splitext(os.path.basename(path))[0]
    for a, b in [("full_record_", "full_"), ("panel_", "p_"), ("adaptation_finance", "fin"), ("_usd_", "_"),
                 ("sensitivity_", "sens_"), ("psmsl_sids_station_screening", "station_screening")]:
        n = n.replace(a, b)
    return n[:31]


def build(src_dir, xlsx, readme):
    with pd.ExcelWriter(os.path.join(OUT, xlsx)) as w:
        pd.DataFrame({"README": readme}).to_excel(w, sheet_name="README", index=False)
        for f in sorted(glob.glob(os.path.join(src_dir, "*.csv"))):
            pd.read_csv(f, encoding="utf-8-sig").to_excel(w, sheet_name=sheet_name(f), index=False)
        man = os.path.join(os.path.dirname(src_dir), "data_raw", "manifest.csv")
        pd.read_csv(man).to_excel(w, sheet_name="source_files_manifest", index=False)
    print("wrote", xlsx)


build(os.path.join(ROOT, "figure2_open_data", "data_out"), "Table_S1_Figure2_data.xlsx", [
    "Supplementary Table S1. Every value plotted in Figure 2, the fitted trends (trends_summary) and the longer records.",
    "Produced by Supplementary Code S1 (figure2_open_data/make_figure2.py). Units and processing: see README.md.",
    "station_screening: all PSMSL RLR stations in SIDS, the selection criteria, the station selected per country and why.",
    "ohc_baseline_pentads: the 16 NCEI pentads (equally weighted) used for the 1995-2014 baseline.",
    "trends_summary rows 'b-sens' and 'd-sens': Gan II (Maldives) and HOT without cruises with substituted inputs.",
    "source_files_manifest: URL, retrieval time, size and SHA-256 of every downloaded source file.",
])
build(os.path.join(ROOT, "sids_worked_example", "data_out"), "Table_S2_SIDS_worked_example.xlsx", [
    "Supplementary Table S2. Indicators and screening flags of the worked example (Table 3, Figure 3).",
    "Produced by Supplementary Code S1 (sids_worked_example/make_sids_example.py), which requires the Figure 2 outputs.",
    "Flags: True/False; empty = missing (indicator not computable), never 'not flagged'. n_flags is empty if any flag is missing.",
    "flag_H: station trend above the global altimetric trend over the same valid years (main); flag_H_full_period: above "
    "3.1 mm/yr (1993-2024); flag_H_significant: exceedance significant at the 95% level (combined standard errors).",
    "n_flags is an exploratory equal-contribution count, not a ranking of need, risk or investment priority; E and F are "
    "not independent because both depend on the exposed population.",
    "finance_per_exposed_resident_usd = national commitments 2015-2024 / (mean population 2015-2024 x 2015 share below 5 m); "
    "a contextual normalization, not finance received by low-elevation residents and not a measure of funding adequacy.",
])
