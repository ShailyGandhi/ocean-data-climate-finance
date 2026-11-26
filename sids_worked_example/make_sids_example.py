"""
Worked example of the five-layer framework (Table 1, Figure 1) for the Small Island Developing States (SIDS) with a
qualifying PSMSL tide gauge, open data only. Layers 1-4 are implemented; layer 5 (Finance Mechanisms) is not, beyond
characterizing current flows. It implements a simplified subset of the hazard-exposure-vulnerability logic: there is
no explicit vulnerability or adaptive-capacity indicator, and finance is not a substitute for vulnerability.

Layer 1  Ocean Observations  Relative sea level at one PSMSL tide gauge per country (selected in ../figure2_open_data)
Layer 2  Data Integration    Station -> country; common period 1993-2024; population, exposure and finance by country
Layer 3  Indicators    H  hazard proxy : relative sea-level trend over the station's valid years in 1993-2024
                                         (mm/yr, +/- AR(1)-adjusted s.e.)
                       E  exposure     : share of population living below 5 m elevation (World Bank, 2015)
                       F  finance      : adaptation-related development finance committed 2015-2024 (OECD, 2024 USD)
                                         per resident living below 5 m. Denominator = mean total population 2015-2024
                                         x 2015 share below 5 m, i.e., the same population basis as the per-resident
                                         sensitivity indicator. F is a contextual normalization of NATIONAL commitments,
                                         not finance received by low-elevation residents and not a measure of adequacy.
Layer 4  Decision Support  Binary screening flags (no weights, no composite index):
                       H  trend > global-mean altimetric trend fitted over the SAME valid years as the station
                       E  exposure above the median of the countries with data
                       F  finance per exposed resident below the median of the countries with data
                       Sensitivity: (i) H only where the exceedance is significant at the 95% level (combined s.e.);
                       (ii) H against the full-period global rate (3.1 mm/yr); (iii) E = land below 5 m and
                       F = finance per resident; (iv) Gan II instead of Male for the Maldives; (v) finance of
                       countries that left the DAC List of ODA Recipients during 2015-2024 (no records after their
                       last listed year; here Seychelles after 2017) annualized over their listed years.
                       Significance: two-sided test at the 95% level, |station - global| > 1.96 x combined s.e.
                       (independent errors assumed).
                       n_flags is an exploratory equal-contribution count. E and F are not independent (both depend on
                       the exposed population), so the count is not three independent lines of evidence and is not a
                       ranking of need, risk or investment priority.

Missing data are kept missing: an indicator that cannot be computed gives a missing flag (<NA>), never "not flagged",
and n_flags is reported only when all three flags are available. A country that is absent from the OECD files has
missing finance; for a country that is present, a year without records counts as zero commitments.

Run ../figure2_open_data/make_figure2.py first (or ../run_all.py). Outputs go to ./data_out and ./sids_worked_example.png.
"""
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import provenance  # noqa: E402  (package root: cached, checksummed downloads)

FIG2 = os.path.join(HERE, "..", "figure2_open_data", "data_out")
RAW = os.path.join(HERE, "data_raw")
OUT = os.path.join(HERE, "data_out")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

FIN_YEARS = (2015, 2024)
EXPOSURE_YEAR = 2015  # latest year of the World Bank below-5-m indicators
WB = {"pop_below5m_pct": "EN.POP.EL5M.ZS", "land_below5m_pct": "AG.LND.EL5M.ZS", "population": "SP.POP.TOTL"}

# ---- Layer 1-2: selected stations (one per country) from the Figure 2 screening
scr = pd.read_csv(os.path.join(FIG2, "psmsl_sids_station_screening.csv"), encoding="utf-8-sig")
sel = scr[scr["selected"]].set_index("iso3")
iso = list(sel.index)


def wb_series(indicator):
    u = (f"https://api.worldbank.org/v2/country/{';'.join(iso)}/indicator/{indicator}"
         "?format=json&per_page=5000&date=1990:2025")
    path = provenance.fetch(u, f"wb_{indicator}_{len(iso)}sids.json", RAW, timeout=120)
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)[1]
    df = pd.DataFrame([(r["countryiso3code"], int(r["date"]), r["value"]) for r in rows],
                      columns=["iso3", "year", "value"])
    return df.pivot(index="year", columns="iso3", values="value").reindex(columns=iso).astype(float)


# ---- hazard: station trends and the global altimetric trend over the same valid years
tr = pd.read_csv(os.path.join(FIG2, "trends_summary.csv"), encoding="utf-8-sig")
glob = tr[(tr.panel == "a") & (tr.series == "Global ocean") & (tr.variable == "absolute sea level (linear)")].iloc[0]
GLOBAL_RATE, GLOBAL_SE = glob.trend, glob.se_ar1
alt = pd.read_csv(os.path.join(FIG2, "panel_a_altimetry_sla_mm.csv"), index_col="year")["Global ocean"]
tg = pd.read_csv(os.path.join(FIG2, "panel_b_sids_tide_gauges_rsl_mm.csv"), index_col="year", encoding="utf-8-sig")
gan = pd.read_csv(os.path.join(FIG2, "sensitivity_b_gan_ii_maldives_rsl_mm.csv"), index_col="year").iloc[:, 0]


def ols_trend(x, y):
    """Same estimator as make_figure2.py: OLS slope, s.e. adjusted for lag-1 autocorrelation (n_eff)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    A = np.vstack([x - x.mean(), np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    r1 = np.corrcoef(resid[:-1], resid[1:])[0, 1]
    n_eff = max(n * (1 - r1) / (1 + r1) if r1 > 0 else n, 3.0)
    return coef[0], np.sqrt(resid @ resid / (n_eff - 2) / ((x - x.mean()) ** 2).sum())


def hazard(series):
    s = series.dropna()
    rate, se = ols_trend(s.index, s.values)
    g = alt.reindex(s.index).dropna()
    assert len(g) == len(s), "altimetry missing for a tide-gauge year"
    g_rate, g_se = ols_trend(g.index, g.values)
    return rate, se, g_rate, g_se, f"{s.index.min()}-{s.index.max()}", len(s)


rows = []
for code, c in sel.iterrows():
    col = [k for k in tg.columns if k.endswith(", " + c["country"])][0]
    rate, se, g_rate, g_se, per, n = hazard(tg[col])
    rows.append({"iso3": code, "country": c["country"], "region": c["region"], "station": col.split(",")[0],
                 "psmsl_id": int(c["psmsl_id"]), "rsl_valid_years": n, "rsl_period": per,
                 "rsl_trend_mm_yr": rate, "rsl_trend_se": se,
                 "global_trend_same_years_mm_yr": g_rate, "global_trend_same_years_se": g_se})
ind = pd.DataFrame(rows).set_index("iso3")
# check: the trend re-computed here matches the Figure 2 trend table
fig2_rates = tr[tr.panel == "b"].set_index(tr[tr.panel == "b"].series.str.extract(r"PSMSL (\d+)")[0].astype(int))["trend"]
assert np.allclose(ind.set_index("psmsl_id")["rsl_trend_mm_yr"], fig2_rates.reindex(ind["psmsl_id"]), atol=1e-3)

# ---- exposure and context (World Bank)
pop5, land5, pop = (wb_series(WB[k]) for k in ("pop_below5m_pct", "land_below5m_pct", "population"))
ind["pop_below5m_pct_2015"] = pop5.loc[EXPOSURE_YEAR]
ind["land_below5m_pct_2015"] = land5.loc[EXPOSURE_YEAR]
pop_years = pop.loc[FIN_YEARS[0]:FIN_YEARS[1]]
ind["population_mean_2015_2024"] = pop_years.mean().where(pop_years.count() == len(pop_years))
ind["exposed_population"] = ind["population_mean_2015_2024"] * ind["pop_below5m_pct_2015"] / 100

# ---- finance (OECD, from Figure 2 processing)
fin = pd.read_csv(os.path.join(FIG2, "panel_f_sids_adaptation_finance_by_country_usd_mn_2024.csv"), index_col=0,
                  encoding="utf-8-sig")
fin.columns = fin.columns.astype(int)
# present in the OECD files: a year without records = no commitment (0); absent from the files: missing (NaN)
cum = fin.loc[:, FIN_YEARS[0]:FIN_YEARS[1]].fillna(0).sum(axis=1)
ind["in_oecd_recipient_files"] = ind["country"].isin(fin.index)
ind["adapt_finance_2015_2024_usd_mn"] = ind["country"].map(cum)
ind["finance_per_resident_usd"] = 1e6 * ind["adapt_finance_2015_2024_usd_mn"] / ind["population_mean_2015_2024"]
ind["finance_per_exposed_resident_usd"] = 1e6 * ind["adapt_finance_2015_2024_usd_mn"] / ind["exposed_population"]
# Sensitivity (v): a country that left the DAC List of ODA Recipients has no records after its last listed year (here
# Seychelles after 2017), which the main rule counts as zero. Annualize its commitments over its listed years in the
# window instead (sum / listed years x 10). Interior gaps (a listed year without records) still count as zero.
win = fin.loc[:, FIN_YEARS[0]:FIN_YEARS[1]]
last_year = win.apply(lambda r: r.last_valid_index(), axis=1)
listed_years = (last_year - FIN_YEARS[0] + 1).clip(upper=FIN_YEARS[1] - FIN_YEARS[0] + 1)
n_years = FIN_YEARS[1] - FIN_YEARS[0] + 1
ind["last_year_with_oecd_records"] = ind["country"].map(last_year)
ind["adapt_finance_annualized_listed_years_usd_mn"] = ind["country"].map(cum / listed_years * n_years)
ind["finance_per_exposed_resident_listed_years_usd"] = (1e6 * ind["adapt_finance_annualized_listed_years_usd_mn"]
                                                        / ind["exposed_population"])


# ---- Layer 4 (Decision Support): screening flags with explicit missing values
def flag(cond, *inputs):
    out = pd.Series(cond, index=ind.index).astype("boolean")
    for x in inputs:
        out[x.isna()] = pd.NA
    return out


def above_median(x):
    return flag(x > x.median(skipna=True), x)


def below_median(x):
    return flag(x < x.median(skipna=True), x)


def count(*flags):
    df = pd.concat(flags, axis=1)
    return df.sum(axis=1, skipna=True).astype("Int64").where(df.notna().all(axis=1))


r, g = ind["rsl_trend_mm_yr"], ind["global_trend_same_years_mm_yr"]
diff_se = np.hypot(ind["rsl_trend_se"], ind["global_trend_same_years_se"])
ind["flag_H"] = flag(r > g, r, g)                                          # main: matched period
ind["flag_H_full_period"] = flag(r > GLOBAL_RATE, r)                       # check: 3.1 mm/yr, 1993-2024
# sensitivity: exceedance significant at the 95% level (two-sided test: |r - g| > 1.96 x combined s.e., r > g)
ind["flag_H_significant"] = flag((r - g) > 1.96 * diff_se, r, g)
ind["flag_E"] = above_median(ind["pop_below5m_pct_2015"])
ind["flag_F"] = below_median(ind["finance_per_exposed_resident_usd"])
ind["n_flags"] = count(ind.flag_H, ind.flag_E, ind.flag_F)
ind["n_flags_H_significant"] = count(ind.flag_H_significant, ind.flag_E, ind.flag_F)
ind["flag_E_land"] = above_median(ind["land_below5m_pct_2015"])
ind["flag_F_per_resident"] = below_median(ind["finance_per_resident_usd"])
ind["n_flags_alt_E_F"] = count(ind.flag_H, ind.flag_E_land, ind.flag_F_per_resident)
ind["flag_F_listed_years"] = below_median(ind["finance_per_exposed_resident_listed_years_usd"])
ind["n_flags_F_listed_years"] = count(ind.flag_H, ind.flag_E, ind.flag_F_listed_years)

# sensitivity: Gan II instead of Male for the Maldives (H only; E and F are national)
gr, gse, gg, ggse, gper, gn = hazard(gan)
gan_row = {"station": "Gan II (PSMSL 1707)", "rsl_period": gper, "valid_years": gn, "rsl_trend_mm_yr": gr,
           "rsl_trend_se": gse,
           "global_trend_same_years_mm_yr": gg, "flag_H": gr > gg,
           "flag_H_significant": (gr - gg) > 1.96 * np.hypot(gse, ggse)}
pd.DataFrame([gan_row]).round(3).to_csv(os.path.join(OUT, "sensitivity_maldives_gan_ii.csv"), index=False)

ind = ind.sort_values(["n_flags", "rsl_trend_mm_yr"], ascending=False, na_position="last")
ind.round(3).to_csv(os.path.join(OUT, "sids_indicators_and_flags.csv"), encoding="utf-8-sig")


# ---- Table 3 of the paper, formatted exactly as printed
def _fl(v, letter):
    return "n.a." if pd.isna(v) else (letter if bool(v) else "–")


def _cnt(v):
    return "n.a." if pd.isna(v) else str(int(v))


def _usd(v):
    return "n.a." if pd.isna(v) else f"{v:,.0f}"


t3 = []
for _, rr in ind.iterrows():
    a_, b_ = rr.rsl_period.split("-")
    t3.append({
        "Country": rr.country, "Gauge (PSMSL ID); valid years": f"{rr.station} ({rr.psmsl_id}); {a_}–{b_}",
        "H: relative sea-level trend, mm/yr (±s.e.)":
            f"{rr.rsl_trend_mm_yr:.1f} ± {rr.rsl_trend_se:.1f}" + (" †" if bool(rr.flag_H_significant) else ""),
        "Global trend, same years, mm/yr": f"{rr.global_trend_same_years_mm_yr:.1f}",
        "E: population below 5 m, % (2015)": f"{rr.pop_below5m_pct_2015:.1f}",
        "Land below 5 m, % (2015)": f"{rr.land_below5m_pct_2015:.1f}",
        "F: finance 2015–2024 per resident below 5 m, USD": _usd(rr.finance_per_exposed_resident_usd),
        "Finance per resident, USD": _usd(rr.finance_per_resident_usd),
        "Flags (H E F)": f"{_fl(rr.flag_H, 'H')} {_fl(rr.flag_E, 'E')} {_fl(rr.flag_F, 'F')}",
        "Count": _cnt(rr.n_flags), "Count (H sig.)": _cnt(rr.n_flags_H_significant),
        "Count (alt.)": _cnt(rr.n_flags_alt_E_F)})
t3.append({"Country": "Median (countries with data)",
           "E: population below 5 m, % (2015)": f"{ind.pop_below5m_pct_2015.median():.1f}",
           "Land below 5 m, % (2015)": f"{ind.land_below5m_pct_2015.median():.1f}",
           "F: finance 2015–2024 per resident below 5 m, USD": _usd(ind.finance_per_exposed_resident_usd.median()),
           "Finance per resident, USD": _usd(ind.finance_per_resident_usd.median())})
pd.DataFrame(t3).fillna("").to_csv(os.path.join(OUT, "table3_as_printed.csv"), index=False, encoding="utf-8-sig")

summary = {
    "countries": len(ind),
    "H_full_period_point_estimate": int(ind.flag_H_full_period.sum()),
    "H_matched_period_point_estimate": int(ind.flag_H.sum()),
    "H_significant_95": int(ind.flag_H_significant.sum()),
    "H_changes_matched_vs_full": list(ind.index[ind.flag_H != ind.flag_H_full_period]),
    "median_E_pct": float(ind.pop_below5m_pct_2015.median()),
    "median_F_usd": float(ind.finance_per_exposed_resident_usd.median()),
    "missing_flags": {k: list(ind.index[ind[k].isna()]) for k in ("flag_H", "flag_E", "flag_F")},
    "gan_ii": gan_row,
    "finance_listed_years_sensitivity": {
        "countries_with_trailing_gap": list(ind.index[ind.last_year_with_oecd_records < FIN_YEARS[1]]),
        "flag_F_changes": list(ind.index[ind.flag_F.fillna(False) != ind.flag_F_listed_years.fillna(False)]),
        "count_changes": list(ind.index[(ind.n_flags != ind.n_flags_F_listed_years).fillna(False)]),
    },
}
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2, default=str)
pd.set_option("display.width", 250)
print(ind[["country", "station", "rsl_period", "rsl_trend_mm_yr", "rsl_trend_se", "global_trend_same_years_mm_yr",
           "pop_below5m_pct_2015", "finance_per_exposed_resident_usd", "finance_per_resident_usd", "flag_H",
           "flag_H_full_period", "flag_H_significant", "flag_E", "flag_F", "n_flags", "n_flags_H_significant",
           "n_flags_alt_E_F"]].round(2).to_string())
print(json.dumps(summary, indent=1, default=str))

# ---- figure 3
LABEL_OFFSET = {  # (dx, dy) in points, set by hand so labels do not overlap; Maldives kept inside the right margin
    "Maldives": (-8, 6, "right"), "Tuvalu": (7, 3, "left"), "Seychelles": (0, 9, "center"),
    "Kiribati": (7, -10, "left"), "Marshall Islands": (-8, 6, "right"), "Micronesia": (-7, -12, "right"),
    "Nauru": (0, 9, "center"), "Palau": (7, 3, "left"), "Papua New Guinea": (0, -15, "center"),
    "Samoa": (7, 3, "left"), "Solomon Islands": (7, 3, "left"), "Tonga": (7, 3, "left"),
    "Fiji": (7, -6, "left"), "Vanuatu": (7, 3, "left"), "Singapore": (7, 3, "left"),
    "Mauritius": (7, 3, "left"), "Cuba": (0, -15, "center"), "Cabo Verde": (7, 3, "left"),
}
fig, ax = plt.subplots(1, 2, figsize=(14, 6.4), constrained_layout=True, gridspec_kw={"width_ratios": [1.25, 1]})
a = ax[0]
ok = ind["n_flags"].notna()
a.errorbar(ind["pop_below5m_pct_2015"], ind["rsl_trend_mm_yr"], yerr=ind["rsl_trend_se"], fmt="none",
           ecolor="grey", lw=1, zorder=2)
sc = a.scatter(ind.loc[ok, "pop_below5m_pct_2015"], ind.loc[ok, "rsl_trend_mm_yr"], s=95,
               c=ind.loc[ok, "n_flags"].astype(float), cmap="Reds", vmin=0, vmax=3, edgecolor="k", zorder=3)
if (~ok).any():
    a.scatter(ind.loc[~ok, "pop_below5m_pct_2015"], ind.loc[~ok, "rsl_trend_mm_yr"], s=95, facecolor="white",
              edgecolor="k", hatch="////", zorder=3, label="count not available (missing flag)")
    a.legend(loc="lower right", fontsize=8)
for k, rr in ind.iterrows():
    if pd.isna(rr["pop_below5m_pct_2015"]):
        continue
    dx, dy, ha = LABEL_OFFSET.get(rr["country"], (7, 3, "left"))
    a.annotate(rr["country"], (rr["pop_below5m_pct_2015"], rr["rsl_trend_mm_yr"]), xytext=(dx, dy),
               textcoords="offset points", fontsize=8, ha=ha)
a.axhline(GLOBAL_RATE, ls="--", color="k", lw=1)
a.text(0.99, GLOBAL_RATE, f"global mean 1993–2024: {GLOBAL_RATE:.1f} mm/yr", transform=a.get_yaxis_transform(),
       ha="right", va="top", fontsize=8)
a.axvline(ind["pop_below5m_pct_2015"].median(), ls=":", color="k", lw=1)
a.set_xlim(left=-1, right=max(55, ind["pop_below5m_pct_2015"].max() * 1.12))
a.set_xlabel(f"Population living below 5 m elevation, % (World Bank, {EXPOSURE_YEAR})")
a.set_ylabel("Relative sea-level trend over each station's\nvalid years in 1993–2024, mm/yr (±1 s.e.)")
a.set_title("(a) Hazard proxy (H) vs exposure (E); color = exploratory flag count")
cb = fig.colorbar(sc, ax=a, ticks=[0, 1, 2, 3])
cb.set_label("Number of screening flags (H, E, F; equal contribution)")

b = ax[1]
o = ind.sort_values("finance_per_exposed_resident_usd", na_position="first")
vals = o["finance_per_exposed_resident_usd"]
colors = np.where(o["flag_F"].fillna(False).astype(bool), "#d7301f", "#9ecae1")
b.barh(o["country"], vals.fillna(0), color=colors)
for i, (cname, v) in enumerate(vals.items()):
    if pd.isna(v):
        b.text(vals.min() * 1.1, i, "no OECD recipient data (F missing)", va="center", fontsize=8, color="0.3")
b.set_xscale("log")
b.axvline(vals.median(), ls=":", color="k", lw=1)
b.set_xlabel(f"National adaptation-related finance committed {FIN_YEARS[0]}–{FIN_YEARS[1]}\n"
             "per resident living below 5 m, USD (2024 prices, log scale)")
b.set_title("(b) Finance (F) per exposed resident; red = F flag")
b.tick_params(axis="y", labelsize=8)
for axx in ax:
    axx.grid(alpha=0.3)
fig.savefig(os.path.join(HERE, "sids_worked_example.png"), dpi=300, bbox_inches="tight", pad_inches=0.1)
fig.savefig(os.path.join(HERE, "sids_worked_example.pdf"), bbox_inches="tight", pad_inches=0.1)
print("done")
