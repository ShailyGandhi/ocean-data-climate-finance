# Ocean data and climate finance for SIDS: code and data

Code, derived data and source-data provenance for the article:

> Gandhi, S.; Fakhruddin, B.S.; Diggs, S. **Integrating Ocean Data with Climate Finance to Strengthen Coastal Resilience and Blue Economy Development.** *Sustainability* (MDPI), manuscript sustainability-4547676, under review.

This package is **Supplementary Code S1** of the article. It reproduces Figures 1–4, Table 3 and Supplementary Tables S1–S2 from open data.

- Archived version: Zenodo, https://doi.org/10.5281/zenodo.24425036
- Development version: GitHub, https://github.com/ShailyGandhi/ocean-data-climate-finance

Both contain the same package. **No source data are redistributed.** All six sources are openly available from their providers, and the scripts download them automatically. The package contains the code, every derived table and figure, and a manifest recording the exact source versions used for the paper (URL, retrieval date, SHA-256 checksum).

## What the paper reports, and where it comes from

| Paper item | Produced by | Output files |
|---|---|---|
| Figure 1 (five-layer framework) | `figure1_framework/make_figure1.py` | `figure1_framework/figure1_framework.png/.pdf` |
| Figure 2 (observed ocean change and adaptation finance), Sections 3.1–3.4 | `figure2_open_data/make_figure2.py` | `figure2_open_data/figure2_open_data.png/.pdf`; `figure2_open_data/data_out/*.csv` |
| Table 3, Figure 3 (worked example, 18 SIDS), Section 3.5 | `sids_worked_example/make_sids_example.py` | `sids_worked_example/data_out/table3_as_printed.csv` (Table 3 exactly as printed), `sids_indicators_and_flags.csv` (all indicators, flags and sensitivity tests); `sids_worked_example/sids_worked_example.png/.pdf` |
| Figure 4 (ocean data value chain) | `figure4_value_chain/make_figure4.py` | `figure4_value_chain/figure4_value_chain.png/.pdf` |
| Supplementary Tables S1 and S2 | `build_supplementary_tables.py` | `supplementary/Table_S1_Figure2_data.xlsx`; `supplementary/Table_S2_SIDS_worked_example.xlsx` |

## How to use

**1. Rebuild everything from the original sources** (downloads about 75 MB; takes a few minutes):

```
python run_all.py
```

**2. Use the figures and tables directly:** `supplementary/` (Tables S1–S2) and the `*.png/.pdf` files in each figure folder.

`run_all.py` runs the steps below in order. Each step needs the outputs of the steps before it.

| Step | Script | Purpose |
|---|---|---|
| 1 | `figure1_framework/make_figure1.py` | Figure 1 |
| 2 | `figure2_open_data/make_figure2.py` | Downloads the sources, screens the tide gauges, and builds Figure 2 and all trend tables |
| 3 | `sids_worked_example/make_sids_example.py` | Worked-example indicators, screening flags, sensitivity tests, Figure 3 |
| 4 | `figure4_value_chain/make_figure4.py` | Figure 4 |
| 5 | `build_supplementary_tables.py` | Supplementary Tables S1–S2 |
| 6 | `check_reported_values.py` | Compares the values reported in the paper with the outputs. Stops with an error if any differ while all sources are identical to the paper's versions; if a provider has updated a source, it lists the differences instead |

`provenance.py` is the shared helper module that handles all downloads.

## Data sources

| Variable | Source | Used for |
|---|---|---|
| Absolute sea level, basin means | NOAA Laboratory for Satellite Altimetry (LSA), annual signals retained, no GIA correction | Figure 2a; global reference trend |
| Relative sea level, tide gauges | Permanent Service for Mean Sea Level (PSMSL), RLR annual means | Figure 2b; hazard indicator H |
| Ocean heat content 0–2000 m | NOAA National Centers for Environmental Information (NCEI), basin pentadal series | Figure 2c |
| Surface pH, aragonite saturation | Hawaii Ocean Time-series (HOT) surface CO₂ product, Station ALOHA (version updated 1 January 2026) and its readme | Figure 2d |
| Adaptation-related development finance | OECD climate-related development finance, recipient perspective (CRDF-RP 2014–2024) | Figure 2e–f; finance indicator F |
| Population and land below 5 m, population, GNI per capita | World Bank World Development Indicators (EN.POP.EL5M.ZS, AG.LND.EL5M.ZS, SP.POP.TOTL, NY.GNP.PCAP.CD) | Exposure indicator E; denominator of F |

All sources are downloaded from the providers, and none is redistributed with this package. Their providers' terms apply; cite the providers as listed below.

## Processing summary

| Figure | Processing |
|---|---|
| 2a | Cycle values averaged to annual means; years with < 20 cycles dropped; OLS trend (±1 s.e., adjusted for lag-1 autocorrelation of the residuals: n_eff = n(1 − r₁)/(1 + r₁), n_eff = n when r₁ ≤ 0, minimum 3; r₁ between consecutive valid values); acceleration = 2 × quadratic coefficient, **descriptive, no uncertainty estimated** |
| 2b | Values with PSMSL quality flags removed. All 96 PSMSL stations in the 26 SIDS (UN Member States) that have any PSMSL station are screened (their PSMSL country codes are listed in `make_figure2.py`; the other 12 SIDS have no PSMSL station): ≥ 20 valid years in 1993–2024 and ≥ 10 in 1995–2014; 31 stations in 18 countries qualify. One station per country: the one with the most valid years (no ties occurred). Exception: the Maldives uses Malé (capital) instead of Gan II, and Gan II is reported as a sensitivity case. Wake Island and Palmyra Island (US territories listed under the Marshall Islands and Kiribati codes) are excluded. Full screening: `figure2_open_data/data_out/psmsl_sids_station_screening.csv` |
| 2c | 10²² J → ZJ. Baseline 1995–2014 = unweighted mean of the 16 overlapping pentads lying entirely within it (a constant shift, so trends are unchanged). Trend fitted to the six non-overlapping pentads 1995–1999 … 2020–2024, with an unadjusted OLS s.e. (six values are too few to estimate autocorrelation) |
| 2d | "Surface" = cruise means over 0–30 dbar. −999 = missing; cruises without calculated in situ pH or Ω_ar are dropped (no gap filling). Cruises with substituted or assumed inputs (readme codes a, b, d, e, f, m, n, r; 5 of 304) are kept; a sensitivity trend excludes them |
| 2e–f | Commitments, "includes overlap", USD 2024 constant prices; SIDS matched exactly to the UN-OHRLLS list of SIDS that are UN Member States |
| 3, Table 3 | H: station trend vs the global altimetric trend over the same valid years. E: % of population below 5 m (2015). F: national adaptation-related commitments 2015–2024 per resident below 5 m (mean population 2015–2024 × 2015 share). Flags: H above the matched global trend; E above and F below the median of the countries with data. Significance: two-sided test at the 95% level, |station − global| > 1.96 × combined s.e. (independent errors assumed). Sensitivity tests: significance-based H; land below 5 m and finance per resident; Gan II for the Maldives; finance of Seychelles (no OECD records after 2017, when it left the DAC List of ODA Recipients) annualized over 2015–2017 |

## Missing values (worked example)

- Missing values stay missing. An indicator that cannot be computed gives a missing flag (empty in the CSV), never "not flagged" and never zero.
- The flag count is reported only when all three flags are available.
- Medians are taken over the countries with data.
- A country absent from the OECD recipient files (Singapore) has missing finance. For a country that is present, a year without records counts as zero commitments; Seychelles, which has no records after 2017, is also tested with its commitments annualized over its listed years (no flag changes). `figure2_open_data/data_out/oecd_sids_recipient_matching.csv` lists, for all 38 SIDS, whether and in which years they appear in the OECD files.

## Interpretation limits

- The flag count is an exploratory equal-contribution count. E and F are not independent: both depend on the exposed population.
- The flags are screening information. They are not a ranking of adaptation need, risk or investment priority, and not a funding recommendation.
- F normalizes national commitments by the low-elevation population. It is neither finance received by those residents nor a measure of funding adequacy.
- The finance panels show commitments, not needs or gaps.
- The hazard indicator covers the chronic marine component of coastal hazard only. It does not cover episodic extremes or compound events.

## Repository structure

```
run_all.py                     run every step in order
provenance.py                  cached, checksummed downloads (shared helper)
build_supplementary_tables.py  writes Supplementary Tables S1-S2
requirements.txt
figure1_framework/             Figure 1
figure2_open_data/             Figure 2; data_raw/ (manifest; sources are downloaded here), data_out/ (derived tables)
sids_worked_example/           Table 3 and Figure 3; data_raw/, data_out/
figure4_value_chain/           Figure 4
supplementary/                 Supplementary Tables S1-S2 (xlsx)
reported_values_check.csv      result of the reported-values check
```

## How to cite

Please cite the article and this archive (see `CITATION.cff`):

> Gandhi, S.; Fakhruddin, B.S.; Diggs, S. Code and data for "Integrating Ocean Data with Climate Finance to Strengthen Coastal Resilience and Blue Economy Development" (v1.0.0). Zenodo, 2026. https://doi.org/10.5281/zenodo.[DOI]

Source data:
- "Altimetry data are provided by NOAA Laboratory for Satellite Altimetry."
- PSMSL: Holgate, S.J. et al. (2013). New data systems and products at the Permanent Service for Mean Sea Level. *J. Coastal Res.* 29, 493–504.
- NCEI ocean heat content: Levitus, S. et al. (2012). World ocean heat content and thermosteric sea level change (0–2000 m), 1955–2010. *Geophys. Res. Lett.* 39, L10603.
- HOT: Dore, J.E. et al. (2009). Physical and biogeochemical modulation of ocean acidification in the central North Pacific. *PNAS* 106, 12235–12240.
- OECD climate-related development finance, recipient perspective; World Bank World Development Indicators. Retrieval dates are in the manifests.

## License

- Code: MIT License (`LICENSE`).
- Derived data, figures and documentation produced by this package: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Source data ( downloaded from the providers).

